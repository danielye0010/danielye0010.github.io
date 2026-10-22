"""Exp08 adapters around unchanged geometry and established Boolean libraries."""
from pathlib import Path
import sys, os, json, time, hashlib
ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parents[1]
sys.dont_write_bytecode = True
sys.path.insert(0, str(PROJECT)); sys.path.insert(0, str(ROOT/'vendor'))
os.environ['MPLCONFIGDIR'] = str(ROOT/'.mplconfig')
import numpy as np
import trimesh
import manifold3d as mf
from solid_modeling import AnalyticCSG, Deformation, Plane, SectionOptions, cross_section
from solid_modeling.forward import BoundaryMesh, tessellate_boundary, cut_mesh
from solid_modeling.sections import section_from_loops
from solid_modeling.validation.reference import PolylineDistance, metric, graph_reference

SETTINGS = [dict(level='coarse', spacing=1/32, curve_tolerance=1e-5, sphere_segments=64,
                 section_spacing=1/256, section_tolerance=5e-5, disk_quad_segments=256),
            dict(level='fine', spacing=1/64, curve_tolerance=2e-6, sphere_segments=128,
                 section_spacing=1/512, section_tolerance=1e-5, disk_quad_segments=512)]

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p, data): Path(p).write_text(json.dumps(data, indent=2, allow_nan=False)+'\n', encoding='utf-8')

def orient_input(boundary):
    start = time.perf_counter()
    mesh = trimesh.Trimesh(vertices=boundary.vertices.copy(), faces=boundary.triangles.copy(), process=False)
    trimesh.repair.fix_normals(mesh, multibody=False)
    if mesh.volume < 0: mesh.invert()
    if not mesh.is_watertight or not mesh.is_winding_consistent or mesh.volume <= 0:
        raise RuntimeError('Oriented input failed conventional Trimesh checks')
    return mesh, time.perf_counter()-start

def backend_input(mesh):
    start = time.perf_counter()
    obj = mf.Manifold(mf.Mesh64(np.ascontiguousarray(mesh.vertices, dtype=np.float64),
                               np.ascontiguousarray(mesh.faces, dtype=np.uint64)))
    if obj.status() != mf.Error.NoError or obj.is_empty(): raise RuntimeError(f'Manifold input {obj.status()}')
    obj.num_tri()  # force any lazy construction
    return obj, time.perf_counter()-start

def mesh_from_backend(obj):
    raw = obj.to_mesh64()
    mesh = trimesh.Trimesh(vertices=np.array(raw.vert_properties[:, :3], float), faces=np.array(raw.tri_verts, np.int64), process=False)
    return mesh, raw

def standard_exports(mesh, prefix):
    """Indexed double-precision PLY and 17-digit OBJ; neither silently overwrites."""
    prefix = Path(prefix); prefix.parent.mkdir(parents=True, exist_ok=True)
    paths = [Path(str(prefix)+s) for s in ('.ply', '.obj', '.npz')]
    if any(p.exists() for p in paths): raise FileExistsError(prefix)
    header = f'ply\nformat binary_little_endian 1.0\ncomment Exp08 indexed float64 geometry\nelement vertex {len(mesh.vertices)}\nproperty double x\nproperty double y\nproperty double z\nelement face {len(mesh.faces)}\nproperty list uchar int vertex_indices\nend_header\n'
    records = np.zeros(len(mesh.faces), dtype=[('n', 'u1'), ('indices', '<i4', (3,))])
    records['n'] = 3; records['indices'] = mesh.faces
    with paths[0].open('wb') as fp:
        fp.write(header.encode('ascii')); fp.write(np.asarray(mesh.vertices, '<f8').tobytes()); fp.write(records.tobytes())
    paths[1].write_text(trimesh.exchange.obj.export_obj(mesh, include_normals=False, include_color=False, digits=17))
    np.savez_compressed(paths[2], vertices=mesh.vertices, faces=mesh.faces)
    return paths

def sphere_points(center, radius, count=32768):
    k = np.arange(count); z = 1-2*(k+.5)/count; a = k*np.pi*(3-np.sqrt(5))
    xy = np.sqrt(1-z*z)
    return np.asarray(center)+radius*np.column_stack([xy*np.cos(a), xy*np.sin(a), z])

def intersection_curve(solid, deformation, center, radius, face_anchor, count=2048):
    """Forward-only analytic face/sphere intersection via bracketed radial roots."""
    theta = np.linspace(0, 2*np.pi, count+1)
    directions = np.column_stack([np.zeros(len(theta)), np.cos(theta), np.sin(theta)])
    anchor = np.asarray(face_anchor); low = np.zeros(len(theta)); high = np.full(len(theta), radius*2)
    def equation(t):
        x = anchor+t[:, None]*directions
        return np.sum((deformation.forward_reference(x)-center)**2, axis=1)-radius**2
    if np.any(equation(low) >= 0) or np.any(equation(high) <= 0): raise RuntimeError('Intersection radial reference not bracketed')
    for _ in range(45):
        mid = (low+high)/2; inside = equation(mid) < 0
        low[inside] = mid[inside]; high[~inside] = mid[~inside]
    x = anchor+((low+high)/2)[:, None]*directions
    y = deformation.forward_reference(x); y[-1] = y[0]
    normal = np.linalg.solve(deformation.jacobian(x).transpose(0, 2, 1), np.broadcast_to([-1., 0, 0], x.shape)[:, :, None])[:, :, 0]
    normal /= np.linalg.norm(normal, axis=1)[:, None]
    radial = (y-center)/radius
    sine = np.sqrt(np.maximum(0, 1-np.sum(normal*radial, axis=1)**2))
    return y, dict(reference_range_lo=x.min(axis=0).tolist(), reference_range_hi=x.max(axis=0).tolist(),
        sphere_equation_residual=float(abs(equation((low+high)/2)).max()), minimum_intersection_sine=float(sine.min()))

def prior_inventory():
    out = {}
    for folder in ('experiments', 'solid-query', 'solid_modeling', 'publication_results_2026-09-25', 'paper_figures_final'):
        for p in (PROJECT/folder).rglob('*'):
            if p.is_file() and ROOT not in p.parents and not any(s in ('.venv', '.mplconfig', '__pycache__') for s in p.parts):
                out[str(p)] = sha(p)
    p = Path(r'D:\Users\31746\Downloads\4th_talor_inverse.pdf'); out[str(p)] = sha(p)
    return out
