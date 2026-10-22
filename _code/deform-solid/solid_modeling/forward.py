"""Conventional forward boundary tessellation and triangle/plane cutting.

This is a boundary mesh of the existing analytic family, not a 3D Boolean
engine. Caps use Delaunay triangles with empty circular holes; walls use
parametric quads. Reference FE interfaces are explicit triangle split lines.
"""
from dataclasses import dataclass
import time
import numpy as np
from scipy.spatial import Delaunay
from matplotlib.path import Path as PolygonPath
from .sections import Plane, SectionError, section_from_loops


@dataclass
class BoundaryMesh:
    reference_vertices: np.ndarray
    vertices: np.ndarray
    triangles: np.ndarray
    metadata: dict

    def export(self, path):
        from pathlib import Path
        path = Path(path)
        if path.exists():
            raise FileExistsError(path)
        np.savez_compressed(path, reference_vertices=self.reference_vertices,
                            vertices=self.vertices, triangles=self.triangles)


def knots(lo, hi, spacing):
    values = np.r_[np.linspace(lo, hi, int(np.ceil((hi-lo)/spacing))+1), np.arange(1, 4)/4]
    return np.unique(np.round(values[(values >= lo) & (values <= hi)], 13))


def cylinder_angles(solid, hole, spacing, curve_tolerance):
    x, y, radius = hole
    angle_step = min(spacing/radius, 2*np.arccos(np.clip(1-curve_tolerance/radius, -1, 1)), np.pi/8)
    theta = list(np.linspace(0, 2*np.pi, max(16, int(np.ceil(2*np.pi/angle_step)))+1)[:-1])
    theta.extend([0, np.pi/2, np.pi, 3*np.pi/2])
    for k in np.arange(1, 4)/4:
        for center, sine in ((x, False), (y, True)):
            ratio = (k-center)/radius
            if abs(ratio) < 1:
                a = np.arcsin(ratio) if sine else np.arccos(ratio)
                theta.extend([a % (2*np.pi), ((np.pi-a) if sine else -a) % (2*np.pi)])
    theta = np.unique(np.round(theta, 14))
    return theta


def _clip(poly, axis, value, side):
    out = []
    for a, b in zip(poly, np.roll(poly, -1, axis=0)):
        da, db = side*(a[axis]-value), side*(b[axis]-value)
        ina, inb = da >= -1e-14, db >= -1e-14
        if ina:
            out.append(a)
        if ina != inb:
            p = a+(b-a)*(value-a[axis])/(b[axis]-a[axis]); p[axis] = value
            out.append(p)
    if not out:
        return np.empty((0, 3))
    p = np.array(out)
    keep = np.linalg.norm(p-np.roll(p, 1, axis=0), axis=1) > 1e-13
    return p[keep]


def _split_interfaces(triangles):
    out = []
    for triangle in triangles:
        polys = [triangle]
        for axis in range(3):
            for value in np.arange(1, 4)/4:
                new = []
                for p in polys:
                    if p[:, axis].min() < value-1e-13 and p[:, axis].max() > value+1e-13:
                        for side in (-1, 1):
                            c = _clip(p, axis, value, side)
                            if len(c) >= 3:
                                new.append(c)
                    else:
                        new.append(p)
                polys = new
        for p in polys:
            out.extend(np.array([p[0], p[i], p[i+1]]) for i in range(1, len(p)-1))
    return np.array(out)


def tessellate_boundary(solid, deformation, reference_spacing=1/64, curve_tolerance=1e-5, max_triangles=3_000_000):
    if not np.isfinite(reference_spacing) or reference_spacing <= 0 or not np.isfinite(curve_tolerance) or curve_tolerance <= 0:
        raise ValueError('Positive finite tessellation controls required')
    if reference_spacing < 1/512 or curve_tolerance < 1e-9:
        raise ValueError('Requested mesh exceeds the scoped course-project budget')
    begin = time.perf_counter()
    axes = [knots(solid.lo[i], solid.hi[i], reference_spacing) for i in range(3)]
    rings = []
    for h in solid.holes:
        theta = cylinder_angles(solid, h, reference_spacing, curve_tolerance)
        # One shared rounded reference ring for cap and wall; rounding them
        # independently at different precision can create duplicate seams.
        rings.append(np.round(h[:2]+h[2]*np.column_stack([np.cos(theta), np.sin(theta)]), 13))
    nx, ny, nz = [len(a)-1 for a in axes]
    estimate = 4*(nx+ny)*nz+4*nx*ny+4*sum(len(r) for r in rings)*nz
    if estimate > max_triangles:
        raise SectionError('Boundary mesh triangle budget exhausted; adjust controls explicitly')
    triangles = []
    # Four rectangle walls; common knots make cap/wall seams identical.
    for axis in (0, 1):
        free = [i for i in range(3) if i != axis]
        for position in (solid.lo[axis], solid.hi[axis]):
            a, b = np.meshgrid(axes[free[0]], axes[free[1]], indexing='ij')
            p = np.zeros((*a.shape, 3)); p[..., axis] = position; p[..., free[0]] = a; p[..., free[1]] = b
            triangles.extend(np.stack([p[:-1, :-1], p[1:, :-1], p[1:, 1:]], axis=-2).reshape(-1, 3, 3))
            triangles.extend(np.stack([p[:-1, :-1], p[1:, 1:], p[:-1, 1:]], axis=-2).reshape(-1, 3, 3))
    # Two cap planes with the same ring polygons as the cylinder walls.
    xx, yy = np.meshgrid(axes[0], axes[1])
    xy = np.column_stack([xx.ravel(), yy.ravel()])
    if len(solid.holes):
        inside = (np.linalg.norm(xy[:, None]-solid.holes[None, :, :2], axis=2) <= solid.holes[:, 2]+1e-13).any(axis=1)
        xy = xy[~inside]
        xy = np.concatenate([xy]+rings)
    xy = np.unique(np.round(xy, 13), axis=0)
    faces = Delaunay(xy).simplices
    center = xy[faces].mean(axis=1)
    if len(solid.holes):
        # The cap joins the INSCRIBED ring polygon, rather than the true circle.
        # A true-circle centroid test can incorrectly remove adjacent slivers.
        outside = np.ones(len(center), bool)
        for ring in rings:
            outside &= ~PolygonPath(np.vstack([ring, ring[0]])).contains_points(center)
        faces = faces[outside]
    for z in (solid.lo[2], solid.hi[2]):
        p = np.column_stack([xy, np.full(len(xy), z)])
        triangles.extend(p[faces])
    for ring in rings:
        a = np.broadcast_to(ring[:, None, :], (len(ring), len(axes[2]), 2))
        p = np.concatenate([a, np.broadcast_to(axes[2][None, :, None], (len(ring), len(axes[2]), 1))], axis=2)
        q = np.roll(p, -1, axis=0)
        triangles.extend(np.stack([p[:, :-1], q[:, :-1], q[:, 1:]], axis=-2).reshape(-1, 3, 3))
        triangles.extend(np.stack([p[:, :-1], q[:, 1:], p[:, 1:]], axis=-2).reshape(-1, 3, 3))
    triangles = np.array(triangles)
    # Split only triangles actually crossing a differential description.
    crossing = np.zeros(len(triangles), bool)
    for axis in range(3):
        for value in np.arange(1, 4)/4:
            crossing |= (triangles[:, :, axis].min(axis=1) < value-1e-13) & (triangles[:, :, axis].max(axis=1) > value+1e-13)
    if crossing.any():
        triangles = np.concatenate([triangles[~crossing], _split_interfaces(triangles[crossing])])
    rv, ids = np.unique(np.round(triangles.reshape(-1, 3), 13), axis=0, return_inverse=True)
    faces = ids.reshape(-1, 3)
    keep = np.linalg.norm(np.cross(rv[faces[:, 1]]-rv[faces[:, 0]], rv[faces[:, 2]]-rv[faces[:, 0]]), axis=1) > 1e-16
    faces = faces[keep]
    edges = np.sort(np.concatenate([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]]), axis=1)
    _, edge_counts = np.unique(edges, axis=0, return_counts=True)
    if np.any(edge_counts != 2):
        raise SectionError(f'Analytic boundary tessellation has {int((edge_counts != 2).sum())} nonmanifold/open edges')
    xyz = deformation.forward_reference(rv)
    setup_s = time.perf_counter()-begin
    # Untimed independent diagnostic: sample triangle centroid interpolation.
    refcenter = rv[faces].mean(axis=1)
    defect = np.linalg.norm(deformation.forward_reference(refcenter)-xyz[faces].mean(axis=1), axis=1)
    return BoundaryMesh(rv, xyz, faces, dict(reference_spacing=reference_spacing, curve_tolerance=curve_tolerance,
        vertices=len(rv), triangles=len(faces), geometry_preprocessing_s=setup_s,
        diagnostic_s=time.perf_counter()-begin-setup_s, preprocessing_s=time.perf_counter()-begin,
        watertight_edge_check=True,
        sampled_forward_interpolation_defect=float(defect.max(initial=0)),
        assumptions='analytic nonoverlapping through holes; FE interface split; guarded binary64'))


def cut_mesh(mesh, plane, join_tolerance=1e-10):
    begin = time.perf_counter()
    xyz = mesh.vertices[mesh.triangles]
    distance = plane.distance(xyz)
    eps = 2e-12
    crossing = (distance.min(axis=1) <= eps) & (distance.max(axis=1) >= -eps)
    if np.any((abs(distance[crossing]) <= eps).all(axis=1)):
        raise SectionError('Coplanar mesh triangles: degenerate plane cut requires an explicit contact policy')
    segments = []
    touches = 0
    for triangle, d in zip(xyz[crossing], distance[crossing]):
        hits = []
        for a, b in ((0, 1), (1, 2), (2, 0)):
            if abs(d[a]) <= eps:
                hits.append(triangle[a])
            if d[a]*d[b] < 0 and abs(d[a]) > eps and abs(d[b]) > eps:
                hits.append(triangle[a]+d[a]/(d[a]-d[b])*(triangle[b]-triangle[a]))
        unique = []
        for p in hits:
            if not any(np.linalg.norm(p-q) < eps for q in unique):
                unique.append(p)
        if len(unique) == 2 and np.linalg.norm(unique[0]-unique[1]) > eps:
            segments.append(plane.coordinates(np.array(unique)))
        elif len(unique) == 1:
            touches += 1
        elif len(unique) > 2:
            raise SectionError('Unresolved triangle-plane intersection')
    if not segments:
        return section_from_loops(plane, [], dict(method='forward triangle-plane cut', timing=dict(total_s=time.perf_counter()-begin)))
    seg = np.array(segments)
    points, ids = np.unique(np.round(seg.reshape(-1, 2)/join_tolerance).astype(np.int64), axis=0, return_inverse=True)
    coordinates = np.zeros((len(points), 2)); counts = np.bincount(ids)
    np.add.at(coordinates, ids, seg.reshape(-1, 2)); coordinates /= counts[:, None]
    edges = np.unique(np.sort(ids.reshape(-1, 2), axis=1), axis=0)
    edges = edges[edges[:, 0] != edges[:, 1]]
    adjacency = [[] for _ in points]
    for a, b in edges:
        adjacency[a].append(int(b)); adjacency[b].append(int(a))
    if any(len(a) != 2 for a in adjacency):
        raise SectionError('Plane cut has open/branching graph; decrease join tolerance or avoid tangency')
    unseen = set(range(len(points))); curves = []
    while unseen:
        start = min(unseen); chain = [start]; prev = None; current = start
        while True:
            unseen.discard(current)
            neighbors = adjacency[current]
            nxt = neighbors[0] if neighbors[0] != prev else neighbors[1]
            if nxt == start:
                chain.append(start); break
            if nxt not in unseen:
                raise SectionError('Non-simple plane-cut graph')
            chain.append(nxt); prev, current = current, nxt
        curves.append(coordinates[chain])
    section = section_from_loops(plane, curves)
    section.metadata = dict(method='forward triangle-plane cut', mesh=mesh.metadata,
                            join_tolerance=join_tolerance, isolated_triangle_touches=touches,
                            timing=dict(total_s=time.perf_counter()-begin),
                            topology_status='sampled polygons only; no topology certification')
    return section
