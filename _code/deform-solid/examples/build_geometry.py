"""Generate the four-hole solid and real 3D cut-order outputs."""
from pathlib import Path
import argparse,json,sys
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'course_project')]
from application_geometry import algorithms,map_mesh

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=Path('output'))
    args=parser.parse_args();out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    a,v,_=algorithms(out/'.mplconfig')
    solid=a.AnalyticCSG();identity=a.Deformation('identity');deformation=a.Deformation('nonlinear_high')
    reference,_=a.orient_input(a.tessellate_boundary(solid,identity,reference_spacing=1/32,curve_tolerance=1e-5))
    deformed,_=a.orient_input(a.tessellate_boundary(solid,deformation,reference_spacing=1/32,curve_tolerance=1e-5))
    b0=a.mf.Manifold.sphere(.045,64).translate([.0525,.18,.62])
    b1=a.mf.Manifold.sphere(.045,64).translate([.09942443490438002,.183131631211526,.6264289927536667])
    r,_=a.backend_input(reference);d,_=a.backend_input(deformed)
    reference_cut,_=a.mesh_from_backend(r-b0)
    cut_first,mapping=map_mesh(reference_cut,deformation,a)
    tool_mesh,_=a.mesh_from_backend(b0)
    tool,_=map_mesh(tool_mesh,deformation,a)
    transported,_=a.backend_input(tool)
    after_mesh,_=a.mesh_from_backend(d-b1)
    transported_mesh,_=a.mesh_from_backend(d-transported)
    meshes=dict(reference=reference,deformed=deformed,cut_first=cut_first,
        cut_after=after_mesh,transported=transported_mesh)
    results=dict(model='nonlinear_high',reference_spacing=1/32,curve_tolerance=1e-5,
        sphere_segments=64,coordinate_units='dimensionless',meshes={},sections={})
    for name,mesh in meshes.items():
        a.standard_exports(mesh,out/name)
        results['meshes'][name]=dict(vertices=len(mesh.vertices),triangles=len(mesh.faces),
            volume=float(mesh.volume),watertight=bool(mesh.is_watertight),
            winding_consistent=bool(mesh.is_winding_consistent),euler_number=int(mesh.euler_number))
        if not mesh.is_watertight or not mesh.is_winding_consistent or mesh.volume<=0:
            raise RuntimeError('Invalid output mesh: '+name)
        if name in ('cut_first','cut_after','transported'):
            results['sections'][name]=[]
            for i,z in enumerate([.6264289927536667,.6489289927536667,.7164289927536667]):
                boundary=a.BoundaryMesh(np.asarray(mesh.vertices),np.asarray(mesh.vertices),np.asarray(mesh.faces),{})
                section=a.cut_mesh(boundary,a.Plane([0,0,z],[1,0,0],[0,1,0]))
                section.export(out/f'{name}_section_{i}')
                results['sections'][name].append(dict(height=z,components=section.components,holes=section.holes))
                if section.components!=1 or section.holes!=4:raise RuntimeError('Unexpected section topology')
    (out/'results.json').write_text(json.dumps(results,indent=2)+'\n')
    print(json.dumps(results,indent=2))

if __name__=='__main__':main()
