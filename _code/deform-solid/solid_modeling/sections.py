"""Ordered planar contour geometry; sampling and approximation are distinct.

The grid locates topology, edge roots remove interpolation error, and local
boundary projection refines polygon chords. The chord test samples quarters
and midpoint; neither it nor the grid provides a topology certificate.
"""
from dataclasses import dataclass, field
from pathlib import Path
import csv
import json
import time
import numpy as np
import contourpy
from matplotlib.path import Path as PolygonPath
from .geometry import AnalyticCSG
from .deformation import Deformation


class SectionError(RuntimeError):
    """Clipped, degenerate or unresolved sampled contour geometry."""


@dataclass(frozen=True)
class Plane:
    origin: object
    u: object
    v: object

    def __post_init__(self):
        a = np.array([self.origin, self.u, self.v], float)
        if a.shape != (3, 3) or not np.isfinite(a).all():
            raise ValueError('Finite origin and two three-dimensional basis vectors required')
        if not np.allclose(a[1:] @ a[1:].T, np.eye(2), rtol=0, atol=1e-10):
            raise ValueError('In-plane basis must be orthonormal; it is not normalized silently')
        for name, value in zip(('origin', 'u', 'v'), a):
            value.setflags(write=False)
            object.__setattr__(self, name, value)

    @property
    def basis(self):
        return np.stack([self.u, self.v], axis=1)

    @property
    def normal(self):
        return np.cross(self.u, self.v)

    def world(self, uv):
        return self.origin + np.asarray(uv) @ self.basis.T

    def coordinates(self, xyz):
        return (np.asarray(xyz)-self.origin) @ self.basis

    def distance(self, xyz):
        return (np.asarray(xyz)-self.origin) @ self.normal

    def as_dict(self):
        return dict(origin=self.origin.tolist(), u=self.u.tolist(), v=self.v.tolist(),
                    normal=self.normal.tolist())


@dataclass(frozen=True)
class SectionOptions:
    resolution: float = 1/512
    approximation_tolerance: float = 1e-4
    inverse_field_tolerance: float = 1e-10
    minimum_feature: float | None = None
    samples_per_feature: int = 4
    bounds: object = None
    max_grid_points: int = 4_000_000
    max_vertices: int = 1_000_000
    max_refinement_rounds: int = 18

    def __post_init__(self):
        for value in (self.resolution, self.approximation_tolerance, self.inverse_field_tolerance):
            if not np.isfinite(value) or value <= 0:
                raise ValueError('Positive finite resolution and tolerances required')
        if self.minimum_feature is not None and (not np.isfinite(self.minimum_feature) or self.minimum_feature <= 0):
            raise ValueError('Positive finite feature size required')
        if self.samples_per_feature < 2 or self.max_grid_points < 4 or self.max_vertices < 4 or self.max_refinement_rounds < 1:
            raise ValueError('Invalid sampling or resource limit')


def signed_area(points):
    p = np.asarray(points)
    return float(np.sum(p[:-1, 0]*p[1:, 1]-p[1:, 0]*p[:-1, 1])/2)


@dataclass
class Loop:
    points: np.ndarray
    kind: str
    depth: int
    parent: int | None

    @property
    def signed_area(self):
        return signed_area(self.points)

    @property
    def perimeter(self):
        return float(np.linalg.norm(np.diff(self.points, axis=0), axis=1).sum())


@dataclass
class Section:
    plane: Plane
    loops: list
    metadata: dict = field(default_factory=dict)

    @property
    def area(self):
        return float(sum(loop.signed_area for loop in self.loops))

    @property
    def perimeter(self):
        return float(sum(loop.perimeter for loop in self.loops))

    @property
    def components(self):
        return sum(loop.kind == 'outer' for loop in self.loops)

    @property
    def holes(self):
        return sum(loop.kind == 'inner' for loop in self.loops)

    def contains(self, uv):
        uv = np.asarray(uv, float).reshape(-1, 2)
        count = np.zeros(len(uv), int)
        for loop in self.loops:
            count += PolygonPath(loop.points).contains_points(uv)
        return (count % 2) == 1

    def as_dict(self):
        return dict(plane=self.plane.as_dict(), area=self.area, perimeter=self.perimeter,
                    components=self.components, holes=self.holes, metadata=self.metadata,
                    loops=[dict(id=i, kind=c.kind, depth=c.depth, parent=c.parent,
                                signed_area=c.signed_area, perimeter=c.perimeter,
                                uv=c.points.tolist(), xyz=self.plane.world(c.points).tolist())
                           for i, c in enumerate(self.loops)])

    def export(self, prefix):
        """JSON, ordered UV/XYZ CSV, GeoJSON polygons and an even-odd SVG."""
        prefix = Path(prefix)
        prefix.parent.mkdir(parents=True, exist_ok=True)
        paths = [Path(str(prefix)+s) for s in ('.json', '.csv', '.geojson', '.svg')]
        if any(p.exists() for p in paths):
            raise FileExistsError('Contour exports never overwrite existing geometry')
        paths[0].write_text(json.dumps(self.as_dict(), indent=2, allow_nan=False)+'\n')
        with paths[1].open('w', newline='') as fp:
            writer = csv.writer(fp)
            writer.writerow(['loop', 'kind', 'depth', 'parent', 'vertex', 'u', 'v', 'x', 'y', 'z'])
            for i, c in enumerate(self.loops):
                for j, (uv, xyz) in enumerate(zip(c.points, self.plane.world(c.points))):
                    writer.writerow([i, c.kind, c.depth, c.parent, j, *uv, *xyz])
        features = []
        for i, c in enumerate(self.loops):
            if c.kind == 'outer':
                rings = [c.points.tolist()] + [h.points.tolist() for h in self.loops if h.parent == i and h.kind == 'inner']
                features.append(dict(type='Feature', properties=dict(loop=i, plane=self.plane.as_dict()),
                                     geometry=dict(type='Polygon', coordinates=rings)))
        paths[2].write_text(json.dumps(dict(type='FeatureCollection', features=features))+'\n')
        allp = np.concatenate([c.points for c in self.loops]) if self.loops else np.array([[0, 0], [1, 1]])
        lo, hi = allp.min(axis=0), allp.max(axis=0)
        margin = max(float((hi-lo).max())*.03, 1e-6)
        commands = []
        for c in self.loops:
            commands.append('M '+' L '.join(f'{x:.12g},{-y:.12g}' for x, y in c.points[:-1])+' Z')
        view = f'{lo[0]-margin} {-hi[1]-margin} {hi[0]-lo[0]+2*margin} {hi[1]-lo[1]+2*margin}'
        paths[3].write_text(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{view}"><title>Deformed solid cross-section in plane coordinates</title><path d="{" ".join(commands)}" fill="#e6e6e6" fill-rule="evenodd" stroke="#222" stroke-width="{margin/20}"/></svg>\n')
        return paths


def section_from_loops(plane, curves, metadata=None):
    """Validate closure, classify nesting and orient outer CCW / inner CW."""
    clean = []
    for points in curves:
        p = np.asarray(points, float)
        if p.ndim != 2 or p.shape[1] != 2 or not np.isfinite(p).all():
            raise SectionError('Invalid contour coordinates')
        if len(p) < 4 or np.linalg.norm(p[-1]-p[0]) > 1e-8:
            raise SectionError('Open or degenerate contour; increase window/resolution')
        p = p.copy(); p[-1] = p[0]
        keep = np.r_[True, np.linalg.norm(np.diff(p, axis=0), axis=1) > 1e-13]
        p = p[keep]
        if not np.array_equal(p[0], p[-1]):
            p = np.vstack([p, p[0]])
        if len(p) < 4 or abs(signed_area(p)) < 1e-16:
            raise SectionError('Zero-area sampled loop')
        clean.append(p)
    clean.sort(key=lambda p: (-abs(signed_area(p)), float(p[:, 0].min()), float(p[:, 1].min())))
    loops = []
    for i, p in enumerate(clean):
        parents = [j for j in range(i) if PolygonPath(clean[j]).contains_point(p[0])]
        parent = parents[-1] if parents else None
        depth = loops[parent].depth+1 if parent is not None else 0
        kind = 'outer' if depth % 2 == 0 else 'inner'
        if (signed_area(p) > 0) != (kind == 'outer'):
            p = p[::-1].copy()
        # Deterministic start vertex, preserving explicit closure.
        j = np.lexsort((p[:-1, 1], p[:-1, 0]))[0]
        p = np.roll(p[:-1], -j, axis=0); p = np.vstack([p, p[0]])
        loops.append(Loop(p, kind, depth, parent))
    return Section(plane, loops, metadata or {})


class Evaluator:
    def __init__(self, solid, deformation, plane, options):
        self.solid, self.deformation, self.plane, self.options = solid, deformation, plane, options
        self.points = 0
        self.inverse_seconds = 0.
        self.max_inverse_bound = 0.
        self.max_forward_residual = 0.

    def evaluate(self, uv, gradient=False):
        uv = np.asarray(uv, float).reshape(-1, 2)
        if not len(uv):
            return (np.empty(0), np.empty((0, 2))) if gradient else np.empty(0)
        xparts, values, gradients = [], [], []
        for p in np.array_split(uv, max(1, int(np.ceil(len(uv)/65536)))):
            y = self.plane.world(p)
            start = time.perf_counter()
            x, bound, detail = self.deformation.inverse(y, self.options.inverse_field_tolerance)
            self.inverse_seconds += time.perf_counter()-start
            self.points += len(p)
            self.max_inverse_bound = max(self.max_inverse_bound, float(bound.max()))
            self.max_forward_residual = max(self.max_forward_residual, detail['newton_max_residual'])
            value, grad, active = self.solid.value_gradient(x)
            values.append(value)
            if gradient:
                world_grad = np.linalg.solve(self.deformation.jacobian(x).transpose(0, 2, 1), grad[:, :, None])[:, :, 0]
                gradients.append(world_grad @ self.plane.basis)
        value = np.concatenate(values)
        return (value, np.concatenate(gradients)) if gradient else value

    def project_normal(self, uv, normals, reach, tolerance):
        """Bracket/bisect boundary roots along fixed polygon chord normals.

        Fixed normals matter near CSG corners: the closest active primitive
        can be a neighboring hole wall rather than the cap being traced.
        Keep the original inverse evaluation at every scalar-root sample.
        """
        p = np.asarray(uv, float)
        f = self.evaluate(p)
        out = p.copy()
        active = np.flatnonzero(abs(f) > self.options.inverse_field_tolerance)
        if not len(active):
            return out
        start = p[active]
        direction = normals[active]
        radius = np.maximum(reach[active], 1e-9)/8
        found = np.zeros((len(active), 2), bool)
        end = np.repeat(start[:, None, :], 2, axis=1)
        fend = np.zeros((len(active), 2))
        pending = np.arange(len(active))
        for _ in range(7):
            if not len(pending):
                break
            trial = start[pending, None, :]+np.array([-1, 1])[None, :, None]*radius[pending, None, None]*direction[pending, None, :]
            values = self.evaluate(trial.reshape(-1, 2)).reshape(-1, 2)
            good = values*f[active[pending], None] <= 0
            end[pending] = trial; fend[pending] = values; found[pending] = good
            pending = pending[~good.any(axis=1)]
            radius[pending] *= 2
        if len(pending):
            raise SectionError('Chord-normal boundary root unbracketed; decrease grid spacing')
        row, side = np.where(found)
        a = start[row].copy(); b = end[row, side].copy(); fa = f[active[row]].copy()
        for _ in range(60):
            if np.max(np.linalg.norm(b-a, axis=1), initial=0) <= tolerance:
                break
            mid = (a+b)/2; fm = self.evaluate(mid)
            left = fa*fm <= 0
            b[left] = mid[left]; a[~left] = mid[~left]; fa[~left] = fm[~left]
        roots = (a+b)/2
        dist = np.linalg.norm(roots-start[row], axis=1)
        best = np.full(len(active), np.inf)
        for i, r in enumerate(row):
            if dist[i] < best[r]:
                out[active[r]] = roots[i]; best[r] = dist[i]
        return out


def default_bounds(solid, deformation, plane, padding):
    """Q1 convex-hull enclosure of the complete physical body, projected to UV."""
    axes = [np.unique(np.r_[solid.lo[j], np.arange(1, 4)/4, solid.hi[j]]) for j in range(3)]
    axes = [a[(a >= solid.lo[j]) & (a <= solid.hi[j])] for j, a in enumerate(axes)]
    points = np.stack(np.meshgrid(*axes, indexing='ij'), axis=-1).reshape(-1, 3)
    uv = plane.coordinates(deformation.forward_reference(points))
    return np.array([uv.min(axis=0)-padding, uv.max(axis=0)+padding])


def edge_roots(curves, axes, evaluator, tolerance):
    p = np.concatenate([c[:-1] for c in curves])
    already = abs(evaluator.evaluate(p)) <= evaluator.options.inverse_field_tolerance
    # Contourpy vertices lie on a grid edge; bracket using that exact edge.
    ix = np.clip(np.searchsorted(axes[0], p[:, 0]), 1, len(axes[0])-1)
    iy = np.clip(np.searchsorted(axes[1], p[:, 1]), 1, len(axes[1])-1)
    dx = np.min(abs(p[:, 0, None]-np.stack([axes[0][ix-1], axes[0][ix]], axis=1)), axis=1)
    dy = np.min(abs(p[:, 1, None]-np.stack([axes[1][iy-1], axes[1][iy]], axis=1)), axis=1)
    horizontal = dy <= dx
    a, b = p.copy(), p.copy()
    a[horizontal, 0] = axes[0][ix[horizontal]-1]; b[horizontal, 0] = axes[0][ix[horizontal]]
    a[~horizontal, 1] = axes[1][iy[~horizontal]-1]; b[~horizontal, 1] = axes[1][iy[~horizontal]]
    fa = evaluator.evaluate(a); fb = evaluator.evaluate(b)
    if np.any((fa*fb > 0) & (np.minimum(abs(fa), abs(fb)) > 1e-12)):
        raise SectionError('Contour edge lacks a valid sign bracket')
    for _ in range(60):
        if np.max(np.linalg.norm(b-a, axis=1), initial=0) <= tolerance:
            break
        mid = (a+b)/2; fm = evaluator.evaluate(mid)
        left = (fa*fm <= 0)
        b[left] = mid[left]; fb[left] = fm[left]
        a[~left] = mid[~left]; fa[~left] = fm[~left]
    roots = (a+b)/2
    roots[already] = p[already]
    out, offset = [], 0
    for c in curves:
        r = roots[offset:offset+len(c)-1]; offset += len(c)-1
        out.append(np.vstack([r, r[0]]))
    return out


def refine_curves(curves, evaluator, options):
    tolerance = options.approximation_tolerance
    root_tol = max(2e-10, min(tolerance*1e-3, 1e-7))
    counts = [len(c)-1 for c in curves]
    pieces = []
    for c in curves:
        p = c[:-1]
        p = p[np.linalg.norm(p-np.roll(p, 1, axis=0), axis=1) > 1e-13]
        if len(p) < 3:
            raise SectionError('Degenerate contour after edge root refinement')
        pieces.append(p)
    max_deviation = 0.
    for round_id in range(options.max_refinement_rounds):
        a = np.concatenate(pieces)
        b = np.concatenate([np.roll(p, -1, axis=0) for p in pieces])
        mid = a[:, None, :]+np.array([.25, .5, .75])[None, :, None]*(b-a)[:, None, :]
        d = b-a; length = np.linalg.norm(d, axis=1)
        normals = np.column_stack([-d[:, 1], d[:, 0]])/np.maximum(length[:, None], 1e-300)
        projected = evaluator.project_normal(mid.reshape(-1, 2), np.repeat(normals, 3, axis=0),
                                             np.repeat(length, 3), root_tol).reshape(-1, 3, 2)
        deviations = np.linalg.norm(projected-mid, axis=2)
        refine = deviations.max(axis=1) > tolerance
        max_deviation = float(deviations.max(initial=0))
        if not refine.any():
            return [np.vstack([p, p[0]]) for p in pieces], dict(refinement_rounds=round_id, sampled_chord_deviation=max_deviation)
        if len(a)+3*refine.sum() > options.max_vertices:
            raise SectionError('Contour vertex budget exhausted')
        new = []; offset = 0
        for p in pieces:
            rows = []
            for i in range(len(p)):
                rows.append(p[i])
                if refine[offset+i]:
                    rows.extend(projected[offset+i])
            new.append(np.array(rows)); offset += len(p)
        pieces = new
    raise SectionError('Sampled polygon approximation tolerance not reached')


def cross_section(solid=None, deformation=None, plane=None, options=None):
    solid = solid or AnalyticCSG()
    deformation = deformation or Deformation()
    plane = plane or Plane([0, 0, .52], [1, 0, 0], [0, 1, 0])
    options = options or SectionOptions()
    begin = time.perf_counter()
    h = options.resolution
    if options.minimum_feature is not None:
        h = min(h, options.minimum_feature/options.samples_per_feature)
    bounds = default_bounds(solid, deformation, plane, 3*h) if options.bounds is None else np.asarray(options.bounds, float)
    if bounds.shape != (2, 2) or not np.isfinite(bounds).all() or np.any(bounds[0] >= bounds[1]):
        raise ValueError('Bounds must be [[u_min,v_min],[u_max,v_max]]')
    n = np.ceil((bounds[1]-bounds[0])/h).astype(int)+1
    if np.prod(n.astype(np.int64)) > options.max_grid_points:
        raise SectionError('Grid budget exhausted; adjust window/resolution explicitly')
    axes = [np.linspace(bounds[0, j], bounds[1, j], n[j]) for j in range(2)]
    uv = np.stack(np.meshgrid(*axes), axis=-1)
    evaluator = Evaluator(solid, deformation, plane, options)
    t = time.perf_counter(); value = evaluator.evaluate(uv.reshape(-1, 2)).reshape(n[1], n[0]); grid_s = time.perf_counter()-t
    if np.any(np.r_[value[0], value[-1], value[:, 0], value[:, -1]] <= 0):
        raise SectionError('Slice intersects the sampling window boundary; enlarge bounds')
    if not np.any(value < 0) and np.any(abs(value) < 1e-12):
        raise SectionError('Coplanar/tangent slice has no resolved material interior')
    t = time.perf_counter()
    curves = contourpy.contour_generator(x=axes[0], y=axes[1], z=value, name='serial', line_type='Separate', corner_mask=False).lines(0)
    extraction_s = time.perf_counter()-t
    for c in curves:
        if np.linalg.norm(c[0]-c[-1]) > 1e-9:
            raise SectionError('Extractor produced an open contour')
    t = time.perf_counter()
    refinement = dict(refinement_rounds=0, sampled_chord_deviation=0.)
    if curves:
        curves = edge_roots(curves, axes, evaluator, max(2e-10, min(options.approximation_tolerance*1e-3, 1e-7)))
        curves, refinement = refine_curves(curves, evaluator, options)
    refinement_s = time.perf_counter()-t
    section = section_from_loops(plane, curves)
    section.metadata = dict(method='Newton implicit section', solid=solid.as_dict(), deformation=deformation.as_dict(),
        resolution_requested=options.resolution, grid_spacing=[float(a[1]-a[0]) for a in axes], grid_shape=n.tolist(),
        bounds=bounds.tolist(), approximation_tolerance=options.approximation_tolerance,
        inverse_field_tolerance=options.inverse_field_tolerance, minimum_feature=options.minimum_feature,
        samples_per_feature=options.samples_per_feature, **refinement,
        inverse_points=evaluator.points, maximum_inverse_bound_inf=evaluator.max_inverse_bound,
        maximum_forward_residual=evaluator.max_forward_residual,
        timing=dict(grid_s=grid_s, extraction_s=extraction_s, refinement_s=refinement_s,
                    inverse_s=evaluator.inverse_seconds, total_s=time.perf_counter()-begin),
        topology_status='sampled loops only; no topology certification',
        approximation_status='quarter/midpoint projection estimator; not a continuous error certificate')
    return section
