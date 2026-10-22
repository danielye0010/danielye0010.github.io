"""Independent mesh, analytic-surface, volume and section checks for Exp08."""
from adapters import *
import pymeshlab as ml
from scipy.special import roots_legendre
from shapely.geometry import Polygon, Point, MultiPolygon, GeometryCollection
from shapely.ops import unary_union

def mesh_checks(mesh, self_intersections=True):
    start = time.perf_counter()
    faces = np.asarray(mesh.faces); tri = np.asarray(mesh.vertices)[faces]
    directed = np.concatenate([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]])
    edges = np.sort(directed, axis=1); unique, inverse, count = np.unique(edges, axis=0, return_inverse=True, return_counts=True)
    directions = np.where(directed[:, 0] < directed[:, 1], 1, -1)
    sums = np.bincount(inverse, weights=directions)
    area2 = np.linalg.norm(np.cross(tri[:, 1]-tri[:, 0], tri[:, 2]-tri[:, 0]), axis=1)
    parts = trimesh.graph.connected_components(mesh.face_adjacency, nodes=np.arange(len(faces)), min_len=1)
    signed = [float(np.einsum('ij,ij->i', tri[p, 0], np.cross(tri[p, 1], tri[p, 2])).sum()/6) for p in parts]
    detected = None; diag_s = 0.
    if self_intersections:
        t = time.perf_counter(); ms = ml.MeshSet()
        ms.add_mesh(ml.Mesh(np.asarray(mesh.vertices, float), np.asarray(mesh.faces, np.int32)))
        ms.apply_filter('compute_selection_by_self_intersections_per_face')
        detected = int(ms.current_mesh().selected_face_number()); diag_s = time.perf_counter()-t
    result = dict(vertices=len(mesh.vertices), triangles=len(faces), non_two_face_edges=int((count != 2).sum()),
        inconsistent_directed_edges=int((sums != 0).sum()), degenerate_triangles=int((area2 <= 1e-18).sum()),
        minimum_double_area=float(area2.min()), boundary_components=len(parts), shell_signed_volumes=signed,
        positive_shells=sum(v > 0 for v in signed), negative_cavity_shells=sum(v < 0 for v in signed),
        material_volume=float(mesh.volume), self_intersecting_faces=detected,
        mesh_check_s=time.perf_counter()-start, self_intersection_s=diag_s)
    result['valid'] = bool(result['non_two_face_edges']==result['inconsistent_directed_edges']==result['degenerate_triangles']==0
                           and mesh.volume>0 and (detected is None or detected==0))
    return result

def volume_reference(solid, deformation, theta_order=16):
    """Integrate det(original Q1 Jacobian) over box minus analytic cylinders.

    Split z at every FE interface, and theta at every xy FE intersection for
    each Gauss radius. This is geometric quadrature of existing maps, not an FE
    simulation. Refinement, not directed rounding, checks its numerical floor.
    """
    g, w = roots_legendre(4)
    axis_points, axis_weights = [], []
    for j in range(3):
        knots = np.r_[solid.lo[j], [.25, .5, .75], solid.hi[j]]
        pts, weight = [], []
        for a, b in zip(knots[:-1], knots[1:]):
            pts.extend((a+b)/2+(b-a)*g/2); weight.extend((b-a)*w/2)
        axis_points.append(np.array(pts)); axis_weights.append(np.array(weight))
    pts = np.stack(np.meshgrid(*axis_points, indexing='ij'), axis=-1).reshape(-1, 3)
    weights = np.prod(np.stack(np.meshgrid(*axis_weights, indexing='ij'), axis=-1), axis=-1).ravel()
    det = np.array([np.linalg.det(deformation.field.jacobian(p)) for p in pts])
    full = float(weights@det); removed = 0.
    tg, tw = roots_legendre(theta_order)
    for hole in solid.holes:
        rp = hole[2]*(g+1)/2; rw = hole[2]*w/2
        for rho, rweight in zip(rp, rw):
            angles = [0., np.pi/2, np.pi, 3*np.pi/2, 2*np.pi]
            for level in (.25, .5, .75):
                for j in (0, 1):
                    ratio = (level-hole[j])/rho
                    if abs(ratio) < 1:
                        if j == 0:
                            a = np.arccos(ratio); angles += [a, 2*np.pi-a]
                        else:
                            a = np.arcsin(ratio); angles += [a % (2*np.pi), (np.pi-a) % (2*np.pi)]
            angles = np.unique(angles)
            for a, b in zip(angles[:-1], angles[1:]):
                theta = (a+b)/2+(b-a)*tg/2; theta_weights = (b-a)*tw/2
                xy = hole[:2]+rho*np.column_stack([np.cos(theta), np.sin(theta)])
                xx = np.repeat(xy, len(axis_points[2]), axis=0)
                zz = np.tile(axis_points[2], len(theta))
                pp = np.column_stack([xx, zz])
                jac = np.array([np.linalg.det(deformation.field.jacobian(p)) for p in pp])
                ww = (theta_weights[:, None]*axis_weights[2][None, :]).ravel()
                removed += float(rweight*rho*(ww@jac))
    return full-removed

def original_samples(solid, deformation, grid=129, theta_count=512, z_count=65):
    points = []
    for axis in range(3):
        free = [j for j in range(3) if j != axis]
        axes = [np.unique(np.r_[np.linspace(solid.lo[j], solid.hi[j], grid), [.25, .5, .75]]) for j in free]
        a, b = np.meshgrid(*axes)
        for v in (solid.lo[axis], solid.hi[axis]):
            p = np.zeros((a.size, 3)); p[:, axis]=v; p[:, free[0]]=a.ravel(); p[:, free[1]]=b.ravel()
            if axis == 2:
                keep = (np.linalg.norm(p[:, None, :2]-solid.holes[None, :, :2], axis=2) >= solid.holes[:, 2]).all(axis=1)
                p=p[keep]
            points.append(p)
    for hole in solid.holes:
        theta = np.linspace(0, 2*np.pi, theta_count, endpoint=False)
        xy = hole[:2]+hole[2]*np.column_stack([np.cos(theta), np.sin(theta)])
        z = np.unique(np.r_[np.linspace(solid.lo[2], solid.hi[2], z_count), [.25, .5, .75]])
        points.append(np.column_stack([np.repeat(xy, len(z), axis=0), np.tile(z, len(xy))]))
    return deformation.forward_reference(np.concatenate(points))

def closest_distances(mesh, points):
    result=[]
    for p in np.array_split(points, max(1, int(np.ceil(len(points)/2048)))):
        result.append(trimesh.proximity.closest_point(mesh, p)[1])
    return np.concatenate(result) if result else np.empty(0)

def output_to_analytic(mesh, solid, deformation, center, radius, seam=None):
    """Distances to VALID analytic patch candidates, not exact nearest surfaces.

    Candidate distances overestimate exact nearest-patch distances, while the
    independently forward-solved seam is a polyline approximation. Distinguish
    this estimator from a certified Hausdorff or dense-point-cloud metric.
    """
    y = np.concatenate([mesh.vertices, mesh.triangles_center])
    values=[]; seam_distance = PolylineDistance([seam]) if seam is not None else None
    for p in np.array_split(y, max(1, int(np.ceil(len(y)/8192)))):
        x, _, _ = deformation.inverse(p); best = np.full(len(p), np.inf)
        candidates=[]
        for axis in range(3):
            for v in (solid.lo[axis], solid.hi[axis]):
                q = np.clip(x, solid.lo, solid.hi); q[:, axis]=v; candidates.append(q)
        for hole in solid.holes:
            q=x.copy(); delta=q[:, :2]-hole[:2]; size=np.linalg.norm(delta, axis=1)
            unit=delta/np.maximum(size[:, None], 1e-300); unit[size<1e-200]=[1, 0]
            q[:, :2]=hole[:2]+hole[2]*unit; q[:, 2]=np.clip(q[:, 2], solid.lo[2], solid.hi[2]); candidates.append(q)
        for q in candidates:
            mapped=deformation.forward_reference(q)
            valid=(solid.value(q)<=1e-10)&(np.linalg.norm(mapped-center, axis=1)>=radius-1e-10)
            d=np.linalg.norm(mapped-p, axis=1); best[valid]=np.minimum(best[valid], d[valid])
        norm=np.linalg.norm(p-center, axis=1); spherical=center+radius*(p-center)/np.maximum(norm[:, None], 1e-300)
        xr, _, _=deformation.inverse(spherical); valid=solid.value(xr)<=1e-10
        best[valid]=np.minimum(best[valid], abs(norm[valid]-radius))
        if seam_distance is not None: best=np.minimum(best, seam_distance.query(p))
        if not np.isfinite(best).all(): raise RuntimeError('No valid analytic boundary candidate')
        values.append(best)
    return np.concatenate(values)

def geometry_checks(mesh, solid, deformation, case, original, seam=None):
    center=np.array(case['center']); radius=case['radius']
    original=original[np.linalg.norm(original-center, axis=1)>=radius]
    spherical=sphere_points(center, radius); xx, _, _=deformation.inverse(spherical)
    spherical=spherical[solid.value(xx)<=0]
    samples=np.concatenate([original, spherical]+([seam] if seam is not None else []))
    d=closest_distances(mesh, samples); reverse=output_to_analytic(mesh, solid, deformation, center, radius, seam)
    return dict(reference_to_mesh_sampled_max=float(d.max()), output_to_valid_analytic_candidate_max=float(reverse.max()),
                bidirectional_sampled_estimator=float(max(d.max(), reverse.max())),
                original_surface_samples=len(original), sphere_surface_samples=len(spherical), output_samples=len(reverse)), samples, d, reverse

def as_polygon(section):
    polygons=[]
    for i, loop in enumerate(section.loops):
        if loop.kind=='outer':
            holes=[c.points for c in section.loops if c.kind=='inner' and c.parent==i]
            polygons.append(Polygon(loop.points, holes))
    result=unary_union(polygons)
    if not result.is_valid: raise RuntimeError('Invalid independent section polygon')
    return result

def polygon_section(geometry, plane):
    if geometry.is_empty: return section_from_loops(plane, [])
    parts=[geometry] if geometry.geom_type=='Polygon' else list(geometry.geoms)
    curves=[]
    for p in parts:
        if p.geom_type!='Polygon':
            if not p.is_empty: raise RuntimeError('Unexpected nonpolygon regular section')
            continue
        curves.append(np.asarray(p.exterior.coords)); curves.extend(np.asarray(r.coords) for r in p.interiors)
    return section_from_loops(plane, curves)

def subtract_disk(section, center, radius, quad_segments):
    distance=float(section.plane.distance(np.array(center)))
    if abs(distance)>=radius:
        return section_from_loops(section.plane, [c.points for c in section.loops]), None, 0.
    r=np.sqrt(radius**2-distance**2); uv=section.plane.coordinates(np.array(center))
    disk=Point(uv).buffer(r, quad_segs=quad_segments)
    output=polygon_section(as_polygon(section).difference(disk), section.plane)
    return output, polygon_section(disk, section.plane), float(r)

def section_checks(output, body, sphere, solid, deformation, case, setting, plane_height):
    center=np.array(case['center']); radius=case['radius']
    plane=Plane([0, 0, plane_height], [1, 0, 0], [0, 1, 0])
    route_a=cut_mesh(BoundaryMesh(None, output.vertices, output.faces, {}), plane)
    original=cross_section(solid, deformation, plane, SectionOptions(resolution=setting['section_spacing'], approximation_tolerance=setting['section_tolerance']))
    route_b, disk, r=subtract_disk(original, center, radius, setting['disk_quad_segments'])
    analytic_original=graph_reference(solid, deformation, plane, 16384)
    ref, refdisk, rr=subtract_disk(analytic_original, center, radius, 2048)
    bodycut=cut_mesh(BoundaryMesh(None, body.vertices, body.faces, {}), plane)
    body_error=metric([c.points for c in bodycut.loops], [c.points for c in analytic_original.loops])['hausdorff_sampled']
    original_error=metric([c.points for c in original.loops], [c.points for c in analytic_original.loops])['hausdorff_sampled']
    sphere_error=0.; sphere_area_error=sphere_perimeter_error=0.
    if r:
        spherecut=cut_mesh(BoundaryMesh(None, sphere.vertices, sphere.faces, {}), plane)
        sphere_error=metric([c.points for c in spherecut.loops], [c.points for c in refdisk.loops])['hausdorff_sampled']
        sphere_area_error=abs(spherecut.area-np.pi*r*r); sphere_perimeter_error=abs(spherecut.perimeter-2*np.pi*r)
    sag=r*(1-np.cos(np.pi/(4*setting['disk_quad_segments']))) if r else 0.
    # Predeclared conservative empirical component-error budget, not a theorem.
    budget=4*(body_error+original_error+sphere_error+sag+6e-7)
    area_budget=(analytic_original.perimeter+2*np.pi*r)*budget+np.pi*budget**2
    perimeter_budget=8*np.pi*budget+sphere_perimeter_error+abs(original.perimeter-analytic_original.perimeter)
    pair=metric([c.points for c in route_a.loops], [c.points for c in route_b.loops])['hausdorff_sampled']
    ea=metric([c.points for c in route_a.loops], [c.points for c in ref.loops])['hausdorff_sampled']
    eb=metric([c.points for c in route_b.loops], [c.points for c in ref.loops])['hausdorff_sampled']
    counts=(route_a.components==route_b.components==ref.components and route_a.holes==route_b.holes==ref.holes)
    data=dict(plane_height=plane_height, disk_radius=r, route_a_area=route_a.area, route_b_area=route_b.area,
        route_a_perimeter=route_a.perimeter, route_b_perimeter=route_b.perimeter,
        route_a_components=route_a.components, route_b_components=route_b.components,
        route_a_holes=route_a.holes, route_b_holes=route_b.holes, counts_match=bool(counts),
        pair_sampled_distance=pair, route_a_reference_error=ea, route_b_reference_error=eb,
        area_difference=abs(route_a.area-route_b.area), perimeter_difference=abs(route_a.perimeter-route_b.perimeter),
        body_only_section_error=body_error, sphere_only_section_error=sphere_error, original_module_section_error=original_error,
        disk_sagitta=sag, empirical_geometry_budget=budget, empirical_area_budget=area_budget, empirical_perimeter_budget=perimeter_budget)
    data['within_budget']=bool(counts and pair<=budget and data['area_difference']<=area_budget and data['perimeter_difference']<=perimeter_budget)
    return data, route_a, route_b, ref, analytic_original
