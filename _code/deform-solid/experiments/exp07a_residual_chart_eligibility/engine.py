"""Read-only chart reuse; fast adapters for the same maps and damped Newton."""
from pathlib import Path
import sys,importlib.util,itertools,time,math
from fractions import Fraction
import numpy as np
from scipy.spatial import cKDTree
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parent;PROJECT=ROOT.parents[1]
PARENT=PROJECT/'experiments/exp06_implicit_boundary_consistency'
spec=importlib.util.spec_from_file_location('exp06_core',PARENT/'core.py')
frozen=importlib.util.module_from_spec(spec);spec.loader.exec_module(frozen)
sys.path.insert(0,str(ROOT))
from sq.field import AFFINE_A,AFFINE_B,BITS
L_INF=math.sqrt(2);RESIDUAL_PAD=2e-13;FIELD_PAD=2e-13;NEWTON_STOP=1e-14

class Model:
    def __init__(self,name,field=None):
        self.name=name;self.field=field or frozen.make_field(name)
        self.q=Fraction({'identity':'0','affine':'7/32','nonlinear_mild':'15/32','nonlinear_high':'15/16'}[name])
        self.q=float(self.q);self.factor=1/(1-self.q)
        self.A=getattr(self.field,'A',np.eye(3));self.Ai=getattr(self.field,'Ai',np.eye(3))
        self.b=getattr(self.field,'shift',np.zeros(3));self.amp=getattr(self.field,'amplitude',0.)
        self.affine_inverse=np.linalg.inv(AFFINE_A)

    @staticmethod
    def tent(x):
        z=np.clip(x,0.,1.);k=np.minimum((z*4).astype(int),3)
        slopes=np.array([3.,1.,-3.,-1.]);values=np.array([0.,.75,1.,.25])
        f=values[k]+(z-k/4)*slopes[k]
        d=slopes[k]*((x>=0)&(x<=1))
        return f,d

    def forward(self,x):
        x=np.asarray(x)
        if self.name=='identity':return x.copy()
        if self.name=='affine':return x+np.clip(x,0,1)@(AFFINE_A-np.eye(3)).T+AFFINE_B
        f,_=self.tent(x);a,b,c=f.T;amp=self.amp
        u=np.column_stack([amp*(b*c/16+a*b/64),amp*(3*a*c/64-b*c/64),amp*(a*b/32+a*b*c/64)])
        return (x+u)@self.A.T+self.b

    def jacobian(self,x):
        if self.name=='identity':return np.broadcast_to(np.eye(3),(len(x),3,3)).copy()
        if self.name=='affine':
            active=((x>=0)&(x<=1)).astype(float)
            return np.eye(3)+(AFFINE_A-np.eye(3))[None,:,:]*active[:,None,:]
        f,d=self.tent(x);a,b,c=f.T;p,q,r=d.T;amp=self.amp
        J=np.broadcast_to(np.eye(3),(len(x),3,3)).copy()
        J[:,0,0]+=amp*p*b/64;J[:,0,1]+=amp*q*(c/16+a/64);J[:,0,2]+=amp*r*b/16
        J[:,1,0]+=amp*3*p*c/64;J[:,1,1]-=amp*q*c/64;J[:,1,2]+=amp*r*(3*a-b)/64
        J[:,2,0]+=amp*p*b*(1/32+c/64);J[:,2,1]+=amp*q*a*(1/32+c/64);J[:,2,2]+=amp*r*a*b/64
        return np.einsum('ij,njk->nik',self.A,J)

    def initial(self,y):
        if self.name=='identity':return y.copy()
        if self.name=='affine':return (y-AFFINE_B)@self.affine_inverse.T
        base=(y-self.b)@self.Ai.T
        u=(self.forward(y)-self.b)@self.Ai.T-y
        return base-u

    def bound(self,residual):
        residual=np.asarray(residual)@self.Ai.T
        norm=np.max(abs(residual),axis=1)
        ideal=norm*self.factor
        inverse=(norm+RESIDUAL_PAD)*self.factor
        return ideal,inverse,L_INF*inverse+FIELD_PAD

class Proposal:
    def __init__(self,model):
        begin=time.perf_counter()
        t=time.perf_counter()
        self.charts=frozen.Charts(model.field)
        self.chart_setup_s=time.perf_counter()-t
        t=time.perf_counter()
        self.index=cKDTree(self.charts.spatial)
        self.index_setup_s=time.perf_counter()-t
        t=time.perf_counter()
        self.monomials={1:list(itertools.combinations_with_replacement(range(3),1)),
                        2:list(itertools.combinations_with_replacement(range(3),2)),
                        3:list(itertools.combinations_with_replacement(range(3),3))}
        self.coefficients={1:np.moveaxis(self.charts.A,2,1)}
        for degree,tensor in ((2,self.charts.B),(3,self.charts.C)):
            rows=[]
            for axes in self.monomials[degree]:
                permutations=set(itertools.permutations(axes))
                rows.append(sum(tensor[(slice(None),slice(None))+p] for p in permutations)/math.factorial(degree))
            self.coefficients[degree]=np.stack(rows,axis=1)
        self.polynomial_setup_s=time.perf_counter()-t
        self.total_setup_s=time.perf_counter()-begin

    def select(self,y,route='nearest',shape=None):
        if route=='nearest':return self.index.query(y,workers=1)[1]
        ny,nx=shape;image=y.reshape(ny,nx,3)
        segments,_=self.charts.face_segments(image[:,0,1],float(image[0,0,2]))
        ids=np.full((ny,nx),-1,int)
        for row,ints in enumerate(segments):
            for lo,hi,e in ints:
                mask=(image[row,:,0]>=lo-1e-12)&(image[row,:,0]<=hi+1e-12);ids[row,mask]=e
        return ids.ravel()

    def values(self,y,ids,order):
        valid=ids>=0;result=np.full_like(y,np.nan);e=ids[valid]
        z=y[valid]-self.charts.spatial[e];value=self.charts.centers[e].copy()
        for degree in range(1,order+1):
            for column,axes in enumerate(self.monomials[degree]):
                fac=np.ones(len(z))
                for axis in axes:fac*=z[:,axis]
                value+=self.coefficients[degree][e,column]*fac[:,None]
        result[valid]=value
        return result

def solve(model,y,initial=None,known_residual=None,stop=NEWTON_STOP):
    """Active-set adapter of inherited damped Newton; no new inverse method."""
    start=time.perf_counter();forward_s=jacobian_s=linear_s=0.;forward_points=jac_points=0;iters=0;fallbacks=0
    t=time.perf_counter();x=model.initial(y) if initial is None else initial.copy()
    initial_s=time.perf_counter()-t
    if initial is not None and np.isnan(x).any():
        missing=np.isnan(x).any(axis=1);t=time.perf_counter();x[missing]=model.initial(y[missing]);initial_s+=time.perf_counter()-t
    def forward(p):
        nonlocal forward_s,forward_points
        t=time.perf_counter();v=model.forward(p);forward_s+=time.perf_counter()-t;forward_points+=len(p);return v
    if known_residual is None:r=forward(x)-y
    else:
        r=known_residual.copy();missing=~np.isfinite(r).all(axis=1)
        if missing.any():r[missing]=forward(x[missing])-y[missing]
    for _ in range(30):
        active=np.flatnonzero(np.max(abs(r@model.Ai.T),axis=1)>stop)
        if not len(active):break
        iters+=len(active);xa=x[active].copy();ra=r[active];target=y[active]
        t=time.perf_counter();J=model.jacobian(xa);jacobian_s+=time.perf_counter()-t;jac_points+=len(active)
        t=time.perf_counter();step=np.linalg.solve(J,ra[:,:,None])[:,:,0];linear_s+=time.perf_counter()-t
        old=np.max(abs(ra@model.Ai.T),axis=1);accepted=np.zeros(len(active),bool)
        nextx=xa.copy();nextr=ra.copy();scale=1.
        for _ in range(8):
            pending=np.flatnonzero(~accepted)
            if not len(pending):break
            trial=xa[pending]-scale*step[pending];rr=forward(trial)-target[pending]
            rn=np.max(abs(rr@model.Ai.T),axis=1)
            ok=(rn<old[pending])|(rn<=stop)
            inds=pending[ok];nextx[inds]=trial[ok];nextr[inds]=rr[ok];accepted[inds]=True;scale/=2
        bad=np.flatnonzero(~accepted)
        if len(bad):
            nextx[bad]=xa[bad]-ra[bad]@model.Ai.T
            nextr[bad]=forward(nextx[bad])-target[bad];fallbacks+=len(bad)
        x[active]=nextx;r[active]=nextr
    maxres=float(np.max(abs(r@model.Ai.T))) if len(r) else 0.
    if maxres>3e-13:raise RuntimeError(f'Newton did not converge: {maxres}')
    elapsed=time.perf_counter()-start
    detail=dict(newton_total_s=elapsed,newton_initial_s=initial_s,newton_forward_s=forward_s,
                newton_jacobian_s=jacobian_s,newton_linear_s=linear_s,
                newton_other_s=max(0.,elapsed-initial_s-forward_s-jacobian_s-linear_s),
                newton_forward_points=forward_points,newton_jacobian_points=jac_points,
                newton_point_iterations=iters,newton_fixedpoint_fallbacks=fallbacks,newton_max_residual=maxres)
    return x,r,detail

def labels(value,bound):
    result=np.zeros(len(value),dtype=np.int8)
    result[value+bound<0]=-1;result[value-bound>0]=1
    return result

def pipeline(model,proposal,y,radius,tolerance,order=0,route='nearest',shape=None,return_arrays=False):
    start=time.perf_counter();timing=dict(selection_s=0.,chart_evaluation_s=0.,residual_check_s=0.,
                                         field_decision_s=0.,fallback_s=0.,merge_s=0.)
    if order==0:
        t=time.perf_counter();x,r,detail=solve(model,y);timing['fallback_s']=time.perf_counter()-t
        t=time.perf_counter();_,inv,b=model.bound(r);timing['residual_check_s']=time.perf_counter()-t
        t=time.perf_counter();value=frozen.implicit(x,radius);lab=labels(value,b);timing['field_decision_s']=time.perf_counter()-t
        eligible=np.zeros(len(y),bool)
    else:
        t=time.perf_counter();ids=proposal.select(y,route,shape);timing['selection_s']=time.perf_counter()-t
        t=time.perf_counter();x=proposal.values(y,ids,order);timing['chart_evaluation_s']=time.perf_counter()-t
        valid=np.isfinite(x).all(axis=1)
        t=time.perf_counter();r=np.full_like(y,np.nan);r[valid]=model.forward(x[valid])-y[valid]
        inv=np.full(len(y),np.inf);b=inv.copy();_,iv,bv=model.bound(r[valid]);inv[valid]=iv;b[valid]=bv
        timing['residual_check_s']=time.perf_counter()-t
        t=time.perf_counter();value=np.full(len(y),np.nan);value[valid]=frozen.implicit(x[valid],radius)
        lab=labels(value,b);eligible=valid&(b<=tolerance)&(lab!=0);bad=~eligible
        timing['field_decision_s']=time.perf_counter()-t
        t=time.perf_counter();xx,rr,detail=solve(model,y[bad],initial=x[bad],known_residual=r[bad]);timing['fallback_s']=time.perf_counter()-t
        t=time.perf_counter();x[bad]=xx;r[bad]=rr;_,iv,bv=model.bound(rr);inv[bad]=iv;b[bad]=bv
        value[bad]=frozen.implicit(xx,radius);lab[bad]=labels(value[bad],b[bad]);timing['merge_s']=time.perf_counter()-t
    total=time.perf_counter()-start
    timing.update(detail);timing['total_s']=total;timing['outer_overhead_s']=max(0.,total-sum(timing[k] for k in ('selection_s','chart_evaluation_s','residual_check_s','field_decision_s','fallback_s','merge_s')))
    timing.update(eligible_points=int(eligible.sum()),fallback_points=int((~eligible).sum()) if order else len(y),
                  unresolved_points=int((lab==0).sum()))
    if np.max(b)>tolerance:raise RuntimeError('returned field tolerance not met')
    return (timing,dict(x=x,value=value,bound=b,labels=lab,eligible=eligible)) if return_arrays else timing
