"""Application-only assembly using unchanged section, Q1 and Boolean methods."""
from pathlib import Path
import sys,os
import numpy as np
PROJECT=Path(__file__).resolve().parent.parent
EXP=PROJECT/'experiments/exp08_constructive_boolean'


def algorithms(cache):
    # Initialize the plotting cache before the old adapter's historical env var.
    os.environ['MPLCONFIGDIR']=str(cache)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.figure();plt.close()
    sys.path.insert(0,str(EXP));sys.path.insert(0,str(EXP/'vendor'));sys.path.insert(0,str(PROJECT))
    import adapters,validation,independent_distance
    os.environ['MPLCONFIGDIR']=str(cache)
    return adapters,validation,independent_distance


def load_mesh(path,a):
    with np.load(path,allow_pickle=False) as z:
        return a.trimesh.Trimesh(z['vertices'],z['faces'],process=False)


def map_mesh(mesh,deformation,a):
    """Reuse the validated FE-plane splitter before mapping triangle vertices.

    Also split the exterior clamp planes for a tool that leaves the unit cube.
    Welding/degenerate tolerance follows the existing forward tessellator.
    """
    from solid_modeling.forward import _split_interfaces,_clip
    triangles=np.array(mesh.triangles)
    crossing=np.zeros(len(triangles),bool)
    for axis in range(3):
        for value in (.25,.5,.75):
            crossing|=(triangles[:,:,axis].min(axis=1)<value-1e-13)&(triangles[:,:,axis].max(axis=1)>value+1e-13)
    number=int(crossing.sum())
    if number:triangles=np.concatenate([triangles[~crossing],_split_interfaces(triangles[crossing])])
    clamp_splits=0
    for axis in range(3):
        for value in (0.,1.):
            hit=(triangles[:,:,axis].min(axis=1)<value-1e-13)&(triangles[:,:,axis].max(axis=1)>value+1e-13)
            if not hit.any():continue
            pieces=[]
            for triangle in triangles[hit]:
                for side in (-1,1):
                    poly=_clip(list(triangle),axis,value,side)
                    for j in range(1,len(poly)-1):pieces.append([poly[0],poly[j],poly[j+1]])
            clamp_splits+=int(hit.sum());triangles=np.concatenate([triangles[~hit],np.array(pieces)])
    rv,indices=np.unique(np.round(triangles.reshape(-1,3),13),axis=0,return_inverse=True)
    faces=indices.reshape(-1,3)
    area=np.linalg.norm(np.cross(rv[faces[:,1]]-rv[faces[:,0]],rv[faces[:,2]]-rv[faces[:,0]]),axis=1)
    keep=area>1e-16
    mapped=deformation.forward_reference(rv)
    result=a.trimesh.Trimesh(mapped,faces[keep],process=False)
    defect=np.linalg.norm(deformation.forward_reference(rv[faces[keep]].mean(axis=1))-mapped[faces[keep]].mean(axis=1),axis=1)
    return result,dict(input_triangles=len(mesh.faces),FE_crossing_triangles_split=number,clamp_crossing_triangles_split=clamp_splits,
        discarded_zero_area_triangles=int((~keep).sum()),weld_decimal_places=13,sampled_triangle_mapping_defect=float(defect.max(initial=0)))


class ReferenceCut:
    """Original analytic CSG minus a reference sphere, evaluated by old slicer."""
    def __init__(self,solid,center,radius):
        self.solid=solid;self.center=np.asarray(center);self.radius=radius
        self.lo,self.hi,self.holes=solid.lo,solid.hi,solid.holes
    def value_gradient(self,x):
        x=np.asarray(x).reshape(-1,3);value,gradient,active=self.solid.value_gradient(x)
        delta=x-self.center;norm=np.linalg.norm(delta,axis=1);sphere=self.radius-norm
        take=sphere>value
        gradient[take]=-delta[take]/np.maximum(norm[take,None],1e-300)
        return np.maximum(value,sphere),gradient,np.where(take,6+len(self.holes),active)
    def value(self,x):return self.value_gradient(x)[0]
    def as_dict(self):return dict(reference_body=self.solid.as_dict(),reference_sphere_center=self.center.tolist(),reference_sphere_radius=self.radius,
        operation='max(d0(X),r0-||X-c0||2)',L_inf=float(np.sqrt(3)))


class SectionInverse:
    """Same inverse; enforce the sphere's sqrt(3) field norm conversion."""
    def __init__(self,base):self.base=base
    def __getattr__(self,name):return getattr(self.base,name)
    def inverse(self,y,field_tolerance=1e-10):
        return self.base.inverse(y,field_tolerance*np.sqrt(2/3))


def cap_volume(deformation,solid,center,radius,order):
    """Independent det(Q1) quadrature over the reference spherical cap.

    This cap is inside one Q1 cell, outside all four holes, and away from caps.
    x runs from x=body.lo to sphere right tip; each yz disk uses radial/angular
    quadrature. Original scalar Q1 Jacobians are used, not mesh volume.
    """
    from numpy.polynomial.legendre import leggauss
    center=np.asarray(center);a=solid.lo[0];b=center[0]+radius
    if not center[0]<a<b<.25:raise ValueError('Reference cap contract unavailable')
    if not (.0<center[1]-radius<center[1]+radius<.25 and .5<center[2]-radius<center[2]+radius<.75):raise ValueError('Cap leaves Q1 patch')
    for h in solid.holes:
        if np.linalg.norm(center[:2]-h[:2])<=radius+h[2]:raise ValueError('Cap/through-hole overlap')
    g,w=leggauss(order);xs=(a+b)/2+(b-a)*g/2;xw=(b-a)*w/2
    ts=(g+1)/2;tw=w/2;theta=np.arange(2*order)*2*np.pi/(2*order)
    points=[];weights=[]
    for x,wx in zip(xs,xw):
        R2=radius**2-(x-center[0])**2
        for t,wt in zip(ts,tw):
            rho=np.sqrt(R2*t)
            points.extend(np.column_stack([np.full(len(theta),x),center[1]+rho*np.cos(theta),center[2]+rho*np.sin(theta)]))
            weights.extend(np.full(len(theta),wx*wt*R2/2*2*np.pi/len(theta)))
    det=np.array([np.linalg.det(deformation.field.jacobian(p)) for p in np.array(points)])
    return float(np.array(weights)@det)


def sample_surface(mesh,count):
    a=np.linspace(0,len(mesh.vertices)-1,min(count,len(mesh.vertices)),dtype=int)
    b=np.linspace(0,len(mesh.faces)-1,min(count,len(mesh.faces)),dtype=int)
    return np.concatenate([mesh.vertices[a],mesh.triangles_center[b]])


def pair_distance(first,second,distance,count):
    x,y=sample_surface(first,count),sample_surface(second,count)
    a=distance.query(second,x);b=distance.query(first,y)
    return dict(first_to_second_max=float(a.max()),second_to_first_max=float(b.max()),
        bidirectional_sampled=float(max(a.max(),b.max())),first_samples=len(x),second_samples=len(y)),dict(first_points=x,second_points=y,first_to_second=a,second_to_first=b)
