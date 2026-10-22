"""Adapters around frozen forward maps, inverse jets, and pathwise stitch."""
from pathlib import Path
import ast, sys, itertools
import numpy as np
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parents[1]
sys.path.insert(0, str(PROJECT/'solid-query'))
sys.path.insert(0, str(PROJECT/'solid-query/exp00b'))
from sq.field import Field, BITS
from sq.geometry import Solid
from sq.baselines import newton, Stats
from fields import Deformation
sys.path.insert(0, str(ROOT))

def extract(path, name, namespace):
    tree = ast.parse(path.read_text(encoding='utf-8'))
    nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name]
    assert len(nodes) == 1
    exec(compile(ast.fix_missing_locations(ast.Module(body=nodes,type_ignores=[])),str(path),'exec'),namespace)
    return namespace[name]

full_jet = extract(PROJECT/'experiments/exp03a_modal_local_inverse/src/numerics.py',
                   'full_jet', {'np':np, 'itertools':itertools})
stitch = extract(PROJECT/'experiments/exp03d_multi_element_atlas/src/atlas.py', 'stitch', {})

def make_field(name):
    if name in ('identity','affine'):
        return Field(name)
    return Deformation(dict(name=name, amplitude=1 if name=='nonlinear_mild' else 2,
                            rotation_t=0, stretch_z=1),n=4)

def implicit(x, radius=1/64):
    holes = Solid.holes.copy(); holes[-1,2] = radius
    x = np.asarray(x)
    box = np.maximum(Solid.lo-x, x-Solid.hi).max(axis=-1)
    hole = (holes[:,2]-np.linalg.norm(x[...,None,:2]-holes[:,:2],axis=-1)).max(axis=-1)
    return np.maximum(box,hole)

class Charts:
    def __init__(self, field):
        self.field = field
        self.centers = (field.ref_lo+field.ref_hi)/2
        self.spatial = field.evaluate(self.centers)
        self.coeff = np.zeros((len(self.centers),8,3))
        local = 2*BITS-1
        u = field.nodes-(field.indices[:,None,:]+BITS[None,:,:])/field.n
        for mask in range(8):
            axes = [j for j in range(3) if mask & (1<<j)]
            weights = np.prod(local[:,axes],axis=1)/8/(field.h/2)**len(axes)
            self.coeff[:,mask] = np.einsum('v,evj->ej',weights,u)
        jets=[]
        for c in self.coeff:
            F=np.eye(3)+np.column_stack([c[1<<j] for j in range(3)])
            H=np.zeros((3,3,3));T=np.zeros((3,3,3,3))
            for j,k in itertools.permutations(range(3),2): H[:,j,k]=c[(1<<j)|(1<<k)]
            for j,k,l in itertools.permutations(range(3)): T[:,j,k,l]=c[7]
            jets.append(full_jet(F,H,T))
        self.A=np.array([j[0] for j in jets]);self.B=np.array([j[1] for j in jets]);self.C=np.array([j[2] for j in jets])

    def values(self, spatial, eid):
        z=spatial-self.spatial[eid]
        a=self.centers[eid]+np.einsum('...ij,...j->...i',self.A[eid],z)
        b=a+.5*np.einsum('...ijk,...j,...k->...i',self.B[eid],z,z)
        c=b+np.einsum('...ijkl,...j,...k,...l->...i',self.C[eid],z,z,z)/6
        return np.stack([a,b,c],axis=-2)

    def jacobians(self, x):
        eid,_=self.field._coordinates(x)
        v=x-self.centers[eid];c=self.coeff[eid]
        J=np.broadcast_to(np.eye(3),x.shape[:-1]+(3,3)).copy()
        for j in range(3):
            for mask in range(1,8):
                if mask & (1<<j):
                    fac=np.ones(x.shape[:-1])
                    for k in range(3):
                        if k!=j and mask & (1<<k):fac*=v[...,k]
                    J[..., :,j]+=fac[...,None]*c[:,mask]
        # derivative of clamped base displacement, followed by affine composition
        exterior=(x<0)|(x>1)
        if exterior.any():
            for i in np.flatnonzero(exterior.any(axis=1)): J[i]=self.field.jacobian(x[i])
        return J

    def inverse(self, spatial):
        shape=spatial.shape;x=spatial.reshape(-1,3).copy();target=x.copy()
        for iteration in range(30):
            r=self.field.evaluate(x)-target
            if np.max(np.abs(r))<8e-15:break
            step=np.linalg.solve(self.jacobians(x),r[...,None])[...,0]
            # Same damped Newton rule and fixed-point fallback as 00-A.
            old=np.abs(r).max(axis=1);accepted=np.zeros(len(x),bool);scale=1.
            for _ in range(8):
                trial=x-scale*step
                ok=(np.abs(self.field.evaluate(trial)-target).max(axis=1)<old)&~accepted
                x[ok]=trial[ok];accepted|=ok;scale/=2
                if accepted.all():break
            if not accepted.all():
                # General affine-composed contraction fallback.
                if hasattr(self.field,'Ai'):
                    base=(target[~accepted]-self.field.shift)@self.field.Ai.T
                    xx=x[~accepted];u=(self.field.evaluate(xx)-self.field.shift)@self.field.Ai.T-xx
                    x[~accepted]=base-u
                else:x[~accepted]-=r[~accepted]
        residual=np.abs(self.field.evaluate(x)-target).max()
        if residual>3e-13:raise RuntimeError(f'Newton residual {residual}')
        return x.reshape(shape),float(residual)

    def face_segments(self, rows, height):
        """Forward-only line/bilinear-face roots. No inverse argument or query truth.

        Algebraic elimination is the batched adapter of Exp03D face_candidates.
        Closed cell intervals cover each row; forward Jacobian transversality
        distinguishes entrances/exits. Endpoint duplicates are reconciled.
        """
        patches=[]; meta=[]
        for e in range(len(self.centers)):
            for face in range(6):
                ax=face//2;free=[j for j in range(3) if j!=ax]
                t=np.zeros((4,3));t[:,ax]=face%2;t[:,free]=[[0,0],[1,0],[0,1],[1,1]]
                p=self.field.ref_lo[e]+self.field.h*t
                q=self.field.evaluate(p)
                a=q[0];b=q[1]-a;c=q[2]-a;d=q[3]-q[1]-q[2]+a
                patches.append(np.stack([a,b,c,d],axis=1));meta.append((e,face,ax,free))
        P=np.array(patches);out=[];maxres=0.;mintrans=1.;duplicates=0;disjoint=0;rejected=0;touches=0;multiple=0
        for yy in rows:
            # q_y(u,v)=yy, q_z(u,v)=height
            coeff=P[:,1:,:].copy();coeff[:,0,0]-=yy;coeff[:,1,0]-=height
            hits={};hit_refs={}
            for swap in (False,True):
                Q=coeff[:,:,[0,2,1,3]] if swap else coeff
                aa,bb,cc,ee=Q[:,0,:].T;ff,gg,hh,ii=Q[:,1,:].T
                p0=ff*cc-hh*aa;p1=ff*ee+gg*cc-hh*bb-ii*aa;p2=gg*ee-ii*bb
                disc=p1*p1-4*p0*p2
                for branch in (-1,1):
                    roots=np.full(len(P),np.nan)
                    quadratic=(np.abs(p2)>1e-25)&(disc>=0)
                    qq=-.5*(p1+np.copysign(np.sqrt(np.maximum(disc,0)),p1))
                    with np.errstate(divide='ignore',invalid='ignore'):
                        roots[quadratic]=(qq/p2 if branch==1 else p0/qq)[quadratic]
                        linear=(~quadratic)&(np.abs(p1)>1e-25)
                        if branch==1:roots[linear]=-p0[linear]/p1[linear]
                        den=Q[:,:,2]+Q[:,:,3]*roots[:,None]
                        idx=np.argmax(np.abs(den),axis=1);ix=np.arange(len(P))
                        vv=-(Q[ix,idx,0]+Q[ix,idx,1]*roots)/den[ix,idx]
                    uu=roots
                    if swap:uu,vv=vv,uu
                    good=(uu>=-1e-10)&(uu<=1+1e-10)&(vv>=-1e-10)&(vv<=1+1e-10)
                    for j in np.flatnonzero(good):
                        # Inherited face solver also refines the algebraic seed.
                        u,v=float(uu[j]),float(vv[j])
                        for _ in range(6):
                            rr=coeff[j,:,0]+coeff[j,:,1]*u+coeff[j,:,2]*v+coeff[j,:,3]*u*v
                            if abs(rr).max()<3e-15:break
                            jj=np.column_stack([coeff[j,:,1]+coeff[j,:,3]*v,coeff[j,:,2]+coeff[j,:,3]*u])
                            try:step=np.linalg.solve(jj,rr)
                            except np.linalg.LinAlgError:break
                            u-=step[0];v-=step[1]
                        uu[j],vv[j]=u,v
                        q=P[j,:,0]+P[j,:,1]*uu[j]+P[j,:,2]*vv[j]+P[j,:,3]*uu[j]*vv[j]
                        res=max(abs(q[1]-yy),abs(q[2]-height))
                        if res>1e-10 or min(u,v)<-1e-10 or max(u,v)>1+1e-10:
                            rejected+=1;continue
                        maxres=max(maxres,res)
                        e,face,ax,free=meta[j];ref=self.field.ref_lo[e].copy()
                        ref[ax]+=self.field.h*(face%2);ref[free]+=self.field.h*np.array([uu[j],vv[j]])
                        trans=abs(np.linalg.solve(self.field.jacobian(ref+1e-11*(self.centers[e]-ref)),[1.,0.,0.])[ax])
                        if trans<1e-10:continue # line tangent to face: not a volume entry/exit
                        mintrans=min(mintrans,trans)
                        if any(abs(v-q[0])<1e-9 for v in hits.get(e,[])):duplicates+=1;continue
                        hits.setdefault(e,[]).append(float(q[0]))
                        hit_refs.setdefault(e,[]).append(ref.copy())
            intervals=[]
            for e,hits_e in hits.items():
                retained=[]
                for xx,ref in zip(hits_e,hit_refs[e]):
                    velocity=np.linalg.solve(self.field.jacobian(ref+1e-11*(self.centers[e]-ref)),[1.,0.,0.])
                    # A transverse line can touch a cell edge at a single point
                    # while entering neither side's volume. Test the two local
                    # directions using only the forward differential.
                    enters=False
                    for sign in (-1,1):
                        trial=ref+sign*1e-7*velocity
                        enters|=bool(np.all(trial>self.field.ref_lo[e]-1e-12) and np.all(trial<self.field.ref_hi[e]+1e-12))
                    if not enters:touches+=1
                    else:retained.append(xx)
                h=sorted(retained)
                if len(h)%2:raise RuntimeError(f'unsupported cell-line intersection row {yy}, plane {height}, cell {e}: {h}')
                if len(h)>2:multiple+=1
                # A globally valid warped Q1 cell need not be convex. A line can
                # leave and re-enter the same cell; retain every paired interval.
                for lo,hi in zip(h[::2],h[1::2]):
                    if hi-lo>1e-10:intervals.append((lo,hi,e))
            intervals.sort()
            for left,right in zip(intervals[:-1],intervals[1:]):
                if left[1]-right[0]>2e-9:raise RuntimeError(f'scanline FE overlap row {yy}: {intervals}')
                if right[0]-left[1]>2e-9:disjoint+=1
            out.append(intervals)
        return out,dict(max_forward_face_residual=maxres,min_sampled_transversality=mintrans,root_duplicates=duplicates,disjoint_line_components=disjoint,rejected_face_seeds=rejected,isolated_cell_edge_touches=touches,multiple_cell_line_intervals=multiple)

    def plane_values(self, spatial, truth):
        ny,nx,_=spatial.shape
        segments,checks=self.face_segments(spatial[:,0,1],float(spatial[0,0,2]))
        route=np.full((ny,nx),-1,int)
        offsets=np.zeros((ny,nx,3,3));reverse=offsets.copy();jumps=[];crossings=[]
        for row,ints in enumerate(segments):
            for lo,hi,e in ints:
                mask=(spatial[row,:,0]>=lo-1e-12)&(spatial[row,:,0]<=hi+1e-12);route[row,mask]=e
            for backwards in (False,True):
                seq=ints[::-1] if backwards else ints
                old=np.zeros((3,3));prev=None;last_endpoint=None
                for lo,hi,e in seq:
                    entry=hi if backwards else lo
                    if last_endpoint is not None and abs(entry-last_endpoint)>2e-9:
                        old=np.zeros((3,3));prev=None
                    if prev is not None:
                        xcross=hi if backwards else lo
                        p=np.array([xcross,spatial[row,0,1],spatial[row,0,2]])
                        lv=self.values(p,prev);rv=self.values(p,e)
                        new=np.asarray(stitch(lv,rv,old))
                        if not backwards:
                            jumps.append((p.copy(),lv.copy(),rv.copy(),(lv+old).copy(),(rv+new).copy()))
                            crossings.append((row,xcross,prev,e,*new.ravel()))
                        old=new
                    mask=(route[row]==e)&(spatial[row,:,0]>=lo-1e-12)&(spatial[row,:,0]<=hi+1e-12)
                    (reverse if backwards else offsets)[row,mask]=old
                    prev=e
                    last_endpoint=lo if backwards else hi
        eid,_=self.field._coordinates(truth.reshape(-1,3));eid=eid.reshape(ny,nx)
        inside=((truth>=0)&(truth<=1)).all(axis=2)
        checks['routing_mismatches_interior']=int(((route!=eid)&inside).sum())
        checks['routing_missing_interior']=int(((route<0)&inside).sum())
        if checks['routing_mismatches_interior']:raise RuntimeError('forward routing vs independent inverse disagreement')
        valid=route>=0;fallback=np.repeat(truth[:,:,None,:],3,axis=2)
        raw=fallback.copy();raw[valid]=self.values(spatial[valid],route[valid])
        correct=fallback.copy();correct[inside]=self.values(spatial[inside],eid[inside])
        fixed=fallback.copy();fixed[valid]=self.values(spatial[valid],42)
        checks['exterior_fallback_points']=int((~valid).sum());checks['physical_points']=int(valid.sum())
        return dict(fixed=fixed,correct_source=correct,raw=raw,stitched=raw+offsets,
                    stitched_reverse=raw+reverse),jumps,checks,np.array(crossings),valid

def forward_boundary(field,height,radius,points_per_curve=4096):
    """Independent forward boundary: analytic reference curves + scalar z intersection.

    For fixed reference x,y, each Q1 z segment is affine in reference z.
    No inverse Newton/chart/routing implementation is called here.
    """
    t=np.linspace(0,1,points_per_curve+1);lo,hi=Solid.lo[0],Solid.hi[0]
    xy=np.concatenate([np.column_stack([lo+(hi-lo)*t,np.full_like(t,lo)]),
                       np.column_stack([np.full_like(t,hi),lo+(hi-lo)*t]),
                       np.column_stack([hi-(hi-lo)*t,np.full_like(t,hi)]),
                       np.column_stack([np.full_like(t,lo),hi-(hi-lo)*t])])
    holes=Solid.holes.copy();holes[-1,2]=radius
    theta=np.linspace(0,2*np.pi,points_per_curve+1)
    curves=[xy]+[h[:2]+h[2]*np.column_stack([np.cos(theta),np.sin(theta)]) for h in holes]
    out=[];zmin=1.;zmax=0.;res=0.;min_slope=np.inf
    for xy in curves:
        mapped=[]
        for z in np.arange(5)/4:
            mapped.append(field.evaluate(np.column_stack([xy,np.full(len(xy),z)]))[:,2])
        mapped=np.array(mapped).T;slopes=np.diff(mapped,axis=1)*4;min_slope=min(min_slope,float(slopes.min()))
        if slopes.min()<=0:raise RuntimeError('forward scalar plane intersection not monotone')
        k=np.minimum((mapped<=height).sum(axis=1)-1,3);assert np.all(k>=0)
        idx=np.arange(len(xy));z=k/4+(height-mapped[idx,k])/(mapped[idx,k+1]-mapped[idx,k])/4
        zmin=min(zmin,float(z.min()));zmax=max(zmax,float(z.max()))
        if z.min()<=Solid.lo[2] or z.max()>=Solid.hi[2]:raise RuntimeError('plane cuts solid top/bottom; forward boundary incomplete')
        q=field.evaluate(np.column_stack([xy,z]));res=max(res,float(abs(q[:,2]-height).max()));out.append(q[:,:2])
    return out,dict(reference_z_min=zmin,reference_z_max=zmax,min_vertical_slope=min_slope,forward_plane_residual=res)
