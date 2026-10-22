"""Independent point/triangle projection checks, without dimensional cutoffs.

Trimesh's closest_point region tests use tol.zero for fourth-power dot products;
thin Boolean intersection triangles can be misclassified. Preserve its primary
measurements and independently validate distances with plane/edge projection.
This is a validation algorithm, not a Boolean construction or geometry change.
"""
from adapters import *

def triangle_distances(tri, p):
    a,b,c=tri[:,0],tri[:,1],tri[:,2]; ab=b-a; ac=c-a
    n=np.cross(ab,ac); den=np.einsum('ij,ij->i',n,n)
    projection=p-(np.einsum('ij,ij->i',p-a,n)/den)[:,None]*n
    beta=np.einsum('ij,ij->i',np.cross(projection-a,ac),n)/den
    gamma=np.einsum('ij,ij->i',np.cross(ab,projection-a),n)/den
    inside=(beta>=0)&(gamma>=0)&(beta+gamma<=1)
    distance=np.full(len(p),np.inf)
    distance[inside]=np.linalg.norm(projection[inside]-p[inside],axis=1)
    for start,end in ((a,b),(b,c),(c,a)):
        edge=end-start; length=np.einsum('ij,ij->i',edge,edge)
        t=np.clip(np.einsum('ij,ij->i',p-start,edge)/length,0,1)
        distance=np.minimum(distance,np.linalg.norm(start+t[:,None]*edge-p,axis=1))
    return distance

def query(mesh, points):
    out=[]
    for p in np.array_split(points,max(1,int(np.ceil(len(points)/2048)))):
        candidates=trimesh.proximity.nearby_faces(mesh,p)
        count=np.array([len(c) for c in candidates]); ids=np.concatenate(candidates)
        repeat=np.repeat(p,count,axis=0); distances=triangle_distances(mesh.triangles[ids],repeat)
        out.append(np.minimum.reduceat(distances,np.r_[0,np.cumsum(count)[:-1]]))
    return np.concatenate(out)

def main():
    out=ROOT/'results'
    freeze=out/'DISTANCE_CHECK_FREEZE.json'; assert not freeze.exists()
    dump(freeze,dict(reason='Unexpected identity transverse refinement regression in Trimesh proximity diagnostics',
        source_hash=sha(Path(__file__)), inputs_changed=False, tolerances_changed=False,
        method='dimensionless barycentric plane inclusion, exact segment projection; original Rtree candidate search'))
    # Analytic controls: face, edge, vertex and a skinny triangle.
    tri=np.repeat(np.array([[[0.,0,0],[1.,0,0],[0,1.,0]]]),4,axis=0)
    pts=np.array([[.2,.2,.3],[.8,.8,0],[-.3,-.4,0],[.2,.2,-.7]])
    expected=np.array([.3,np.sqrt(.18),.5,.7]); assert np.allclose(triangle_distances(tri,pts),expected,atol=2e-15)
    thin=np.array([[[0.,0,0],[.001,0,0],[0,.00001,0]]]); pt=np.array([[.0002,.000002,.000003]])
    assert abs(triangle_distances(thin,pt)[0]-3e-6)<1e-15
    import pandas as pd
    primary=pd.read_csv(out/'geometry.csv'); records=[]; checks=[]
    rng=np.random.default_rng(20261012)
    for row in primary.itertuples():
        key=f'{row.field}_{row.level}_{row.configuration}'
        raw=np.load(out/'meshes'/f'{key}.npz'); mesh=trimesh.Trimesh(raw['vertices'],raw['faces'],process=False)
        data=np.load(out/'samples'/f'{key}_geometry.npz'); pts=data['reference_points']; d=query(mesh,pts)
        reverse=data['output_to_valid_analytic_candidate_distances']
        record=row._asdict(); record.pop('Index',None)
        record.update(primary_trimesh_reference_to_mesh_max=row.reference_to_mesh_sampled_max,
            reference_to_mesh_sampled_max=float(d.max()),bidirectional_sampled_estimator=float(max(d.max(),reverse.max())),
            primary_distance_overestimate_max=float(np.max(data['reference_to_mesh_distances']-d)))
        records.append(record)
        ids=np.r_[np.argmax(d),np.argmax(data['reference_to_mesh_distances']-d),rng.integers(0,len(pts),3)]
        for i in ids:
            brute=triangle_distances(mesh.triangles,np.broadcast_to(pts[i],(len(mesh.faces),3))).min()
            assert abs(brute-d[i])<2e-12
            checks.append(dict(case=key,point_index=int(i),accelerated=float(d[i]),exhaustive=float(brute),
                               primary=float(data['reference_to_mesh_distances'][i])))
        np.savez_compressed(out/'samples'/f'{key}_independent_distance.npz',reference_to_mesh_distances=d)
        pd.DataFrame(records).to_csv(out/'geometry_independent.csv',index=False)
        print('Distance check',key,record['bidirectional_sampled_estimator'],flush=True)
    dump(out/'distance_validation.json',dict(status='PASS',analytic_controls=5,exhaustive_checks=checks,
        maximum_exhaustive_gap=max(abs(r['accelerated']-r['exhaustive']) for r in checks),
        primary_trimesh_diagnostics_retained=True,geometry_or_tolerances_changed=False))

if __name__=='__main__': main()
