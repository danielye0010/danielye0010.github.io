"""Independent forward-only section geometry and closed-form controls."""
import ast
from pathlib import Path
import numpy as np
from scipy.special import ellipe
from scipy.spatial import cKDTree
from solid_modeling import Plane
from solid_modeling.deformation import engine
from solid_modeling.sections import section_from_loops

# Reuse the complete, independently checked Exp06 distance search verbatim.
DISTANCE_SOURCE = Path(engine.PROJECT)/'experiments/exp06_implicit_boundary_consistency/geometry_analysis.py'
tree = ast.parse(DISTANCE_SOURCE.read_text())
nodes = [n for n in tree.body if isinstance(n, (ast.ClassDef, ast.FunctionDef)) and n.name in ('PolylineDistance', 'metric')]
namespace = dict(np=np, cKDTree=cKDTree)
exec(compile(ast.fix_missing_locations(ast.Module(body=nodes, type_ignores=[])), str(DISTANCE_SOURCE), 'exec'), namespace)
PolylineDistance, metric = namespace['PolylineDistance'], namespace['metric']


def orthonormal_plane(origin, tangents):
    u = tangents[:, 0]/np.linalg.norm(tangents[:, 0])
    v = tangents[:, 1]-u*(u@tangents[:, 1]); v /= np.linalg.norm(v)
    return Plane(origin, u, v)


def analytic_plane(deformation, kind='horizontal', height=.52):
    if kind == 'vertical':
        origin = np.array([0, .5, 0.])
        T = np.array([[1., 0], [0, 0], [0, 1]])
    else:
        origin = np.array([.5, .5, height])
        T = np.array([[1., 0], [0, 1], [0, 0.]])
        if kind == 'oblique':
            T[2] = [-.22, .16]
    F = engine.AFFINE_A if deformation.name == 'affine' else np.eye(3)
    b = engine.AFFINE_B if deformation.name == 'affine' else np.zeros(3)
    return orthonormal_plane(F@origin+b, F@T), T, F


def analytic_metrics(solid, deformation, kind):
    plane, T, F = analytic_plane(deformation, kind)
    U = F@T
    scale = np.linalg.norm(np.cross(U[:, 0], U[:, 1]))
    width = solid.hi-solid.lo
    if kind == 'vertical':
        holes = solid.holes[abs(solid.holes[:, 1]-.5) < solid.holes[:, 2]]
        halves = np.sqrt(holes[:, 2]**2-(holes[:, 1]-.5)**2)
        material_width = width[0]-2*halves.sum()
        components = len(holes)+1
        area = material_width*width[2]*scale
        perimeter = 2*material_width*np.linalg.norm(U[:, 0])+2*components*width[2]*np.linalg.norm(U[:, 1])
        intervals = sorted([(h[0]-r, h[0]+r) for h, r in zip(holes, halves)])
        starts = [solid.lo[0]]+[b for a, b in intervals]
        ends = [a for a, b in intervals]+[solid.hi[0]]
        curves = []
        for a, b in zip(starts, ends):
            x = np.array([[a, .5, solid.lo[2]], [b, .5, solid.lo[2]],
                          [b, .5, solid.hi[2]], [a, .5, solid.hi[2]], [a, .5, solid.lo[2]]])
            curves.append(plane.coordinates(x@F.T+(engine.AFFINE_B if deformation.name == 'affine' else 0)))
        return dict(area=float(area), perimeter=float(perimeter), components=components, holes=0), section_from_loops(plane, curves)
    area = (width[0]*width[1]-np.pi*np.sum(solid.holes[:, 2]**2))*scale
    singular = np.linalg.svd(U, compute_uv=False)
    ellipse_unit = 4*singular[0]*ellipe(1-(singular[1]/singular[0])**2)
    perimeter = 2*width[0]*np.linalg.norm(U[:, 0])+2*width[1]*np.linalg.norm(U[:, 1])+ellipse_unit*solid.holes[:, 2].sum()
    return dict(area=float(area), perimeter=float(perimeter), components=1, holes=len(solid.holes)), None


def graph_reference(solid, deformation, plane, samples=8192):
    """Forward plane intersection for slices that are graphs in reference z.

    For each analytic side-boundary xy, n dot Phi(x,y,z) is piecewise affine
    in z. Solve it directly on every frozen Q1 z interval, without inverse,
    spatial-field samples, marching squares or triangle plane intersections.
    Positive slope and absence of cap cuts are checked, never presumed.
    """
    lo, hi = solid.lo[:2], solid.hi[:2]
    axes = []
    for j in range(2):
        values = np.unique(np.r_[np.linspace(lo[j], hi[j], samples+1), np.arange(1, 4)/4])
        axes.append(values[(values >= lo[j]) & (values <= hi[j])])
    xy = np.concatenate([np.column_stack([axes[0][:-1], np.full(len(axes[0])-1, lo[1])]),
                         np.column_stack([np.full(len(axes[1])-1, hi[0]), axes[1][:-1]]),
                         np.column_stack([axes[0][:0:-1], np.full(len(axes[0])-1, hi[1])]),
                         np.column_stack([np.full(len(axes[1])-1, lo[0]), axes[1][:0:-1]])])
    curves = [np.vstack([xy, xy[0]])]
    for h in solid.holes:
        theta = list(np.linspace(0, 2*np.pi, samples+1))
        # Include exact reference FE crossings to avoid a kink-sampling floor.
        for level in np.arange(1, 4)/4:
            for j in (0, 1):
                ratio = (level-h[j])/h[2]
                if abs(ratio) < 1:
                    if j == 0:
                        a = np.arccos(ratio); theta += [a, 2*np.pi-a]
                    else:
                        a = np.arcsin(ratio); theta += [a % (2*np.pi), (np.pi-a) % (2*np.pi)]
        theta = np.unique(theta)
        points = h[:2]+h[2]*np.column_stack([np.cos(theta), np.sin(theta)])
        points[-1] = points[0]
        curves.append(points)
    zknots = np.unique(np.r_[solid.lo[2], np.arange(1, 4)/4, solid.hi[2]])
    zknots = zknots[(zknots >= solid.lo[2]) & (zknots <= solid.hi[2])]
    out, min_slope, residual, z_min, z_max = [], np.inf, 0., np.inf, -np.inf
    for xy in curves:
        mapped = np.stack([plane.distance(deformation.forward_reference(np.column_stack([xy, np.full(len(xy), z)]))) for z in zknots], axis=1)
        slopes = np.diff(mapped, axis=1)/np.diff(zknots)
        min_slope = min(min_slope, float(slopes.min()))
        if slopes.min() <= 0 or np.any(mapped[:, 0] >= 0) or np.any(mapped[:, -1] <= 0):
            raise ValueError('Forward graph reference requires positive z slope and no cap intersections')
        k = (mapped <= 0).sum(axis=1)-1; rows = np.arange(len(xy))
        z = zknots[k]-mapped[rows, k]*(zknots[k+1]-zknots[k])/(mapped[rows, k+1]-mapped[rows, k])
        xyz = deformation.forward_reference(np.column_stack([xy, z]))
        residual = max(residual, float(abs(plane.distance(xyz)).max()))
        z_min = min(z_min, float(z.min())); z_max = max(z_max, float(z.max()))
        uv = plane.coordinates(xyz); uv[-1] = uv[0]; out.append(uv)
    return section_from_loops(plane, out, dict(method='independent forward analytic boundary graph',
        samples_per_primitive=samples, minimum_vertical_plane_slope=min_slope,
        reference_z_min=z_min, reference_z_max=z_max, maximum_plane_residual=residual))


def compare(section, reference, exact=None):
    data = metric([c.points for c in section.loops], [c.points for c in reference.loops])
    if not section.loops and reference.loops:
        data = dict(contour_to_reference_max=None, reference_to_contour_max=None, hausdorff_sampled=None)
    truth = exact or dict(area=reference.area, perimeter=reference.perimeter,
                         components=reference.components, holes=reference.holes)
    data.update(area=section.area, perimeter=section.perimeter, components=section.components, holes=section.holes,
                area_absolute_error=abs(section.area-truth['area']), perimeter_absolute_error=abs(section.perimeter-truth['perimeter']),
                topology_matches=(section.components == truth['components'] and section.holes == truth['holes']))
    return data
