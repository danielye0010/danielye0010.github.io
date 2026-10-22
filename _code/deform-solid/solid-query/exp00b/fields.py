"""Affine composition of the original globally invertible Q1 family."""
from fractions import Fraction as F
from itertools import product
import math
import numpy as np
from common import Field,BITS,Box
from bvh import Index


def affine_exact(model):
    t,s=F(model["rotation_t"]),F(model["stretch_z"])
    c=(1-t*t)/(1+t*t)
    v=2*t/(1+t*t)
    A=[[c,-v,F(0)],[v,c,F(0)],[F(0),F(0),s]]
    Ai=[[c,v,F(0)],[-v,c,F(0)],[F(0),F(0),1/s]]
    b=[F(1,2)-sum(row)/2 for row in A]
    return A,Ai,b


class Deformation(Field):
    def __init__(self,model,n=4,guard=2e-12,fast=False):
        self.model,self.fast=model,fast
        self.amplitude=float(model["amplitude"])
        q_exact=F(model["amplitude"])*F(15,32)
        if q_exact>=1 or model["stretch_z"]<=0:
            raise ValueError("global injectivity proof unavailable; state not executed")
        A,Ai,b=affine_exact(model)
        self.A=np.array(A,float)
        self.Ai=np.array(Ai,float)
        self.shift=np.array(b,float)
        self.q_exact=q_exact
        ai_norm=max(sum(abs(v) for v in row) for row in Ai)
        self.alpha_exact=ai_norm/(1-q_exact)
        self.alpha=float(self.alpha_exact)+guard
        super().__init__("nonlinear",n,guard,inverse_bounds=False)
        self.u_nodes*=self.amplitude
        reference=(self.indices[:,None,:]+BITS[None,:,:])/n
        self.nodes=(reference+self.u_nodes)@self.A.T+self.shift
        self.image_lo=self.nodes.min(axis=1)-guard
        self.image_hi=self.nodes.max(axis=1)+guard
        self.index=Index(self.image_lo,self.image_hi)
        self.storage_bytes+=self.index.storage_bytes+self.A.nbytes+self.Ai.nbytes+self.shift.nbytes

    def evaluate(self,x,stats=None):
        if self.fast and np.asarray(x).shape==(3,):
            return self._fast_point(x,stats,False)
        y=super().evaluate(x,stats)
        return y@self.A.T+self.shift

    def jacobian(self,x,stats=None):
        if self.fast:
            return self._fast_point(x,stats,True)
        return self.A@super().jacobian(x,stats)

    def _fast_point(self,x,stats,jac):
        """Same Q1 field, scalar arithmetic control. No new enclosure algorithm."""
        f,d=[],[]
        for value in x:
            z=max(0.,min(1.,float(value)))
            k=min(int(z*4),3)
            slope=(3.,1.,-3.,-1.)[k]
            f.append((0.,.75,1.,.25)[k]+(z-k/4)*slope)
            d.append(slope if 0<=value<=1 else 0.)
        a,b,c=f
        p,q,r=d
        amp=self.amplitude
        if not jac:
            if stats is not None:
                stats.map_evals+=1
            out=np.array([x[0]+amp*(b*c/16+a*b/64),x[1]+amp*(3*a*c/64-b*c/64),
                          x[2]+amp*(a*b/32+a*b*c/64)])
            return self.A@out+self.shift
        if stats is not None:
            stats.jac_evals+=1
        Du=np.array([[p*b/64,q*(c/16+a/64),r*b/16],
                     [3*p*c/64,-q*c/64,r*(3*a-b)/64],
                     [p*b*(1/32+c/64),q*a*(1/32+c/64),r*a*b/64]])
        return self.A@(np.eye(3)+amp*Du)

    def cell_bounds(self,eid,box,stats=None):
        # Inherited range is of X+scaled u; linear composition keeps Q1.
        from sq.field import basis
        corners=np.where(BITS,box.hi,box.lo)
        t=(corners-self.ref_lo[eid])*self.n
        if stats is not None:
            stats.map_evals+=8
        points=(corners+basis(t)@self.u_nodes[eid])@self.A.T+self.shift
        return Box(points.min(axis=0)-self.guard,points.max(axis=0)+self.guard)

    def diagnostics(self):
        ranges=[]
        singular=[]
        for axis in range(3):
            low=np.flatnonzero(BITS[:,axis]==0)
            high=[np.flatnonzero(np.all(BITS==BITS[j]+np.eye(3,dtype=int)[axis],axis=1))[0] for j in low]
            deriv=(self.nodes[:,high]-self.nodes[:,low])*self.n
            ranges.append((deriv.min(axis=1),deriv.max(axis=1)))
        Jlo=np.stack([v[0] for v in ranges],axis=2)
        Jhi=np.stack([v[1] for v in ranges],axis=2)
        absnear=np.maximum(abs(Jlo-np.eye(3)),abs(Jhi-np.eye(3)))
        # Match 00-A: first union each derivative entry over ALL cells,
        # then take the infinity norm. A per-cell norm is tighter but is
        # not the old diagnostic when row maxima occur in different cells.
        qnear=float(np.max(np.sum(absnear.max(axis=0),axis=1)))+self.guard
        qcell=float(np.max(np.sum(absnear,axis=2)))+self.guard
        for e in range(self.n**3):
            for t in list(product((0.,1.),repeat=3))+[(.5,.5,.5)]:
                # Use the fast formula just INSIDE the chosen cell to avoid
                # assigning the wrong one-sided derivative on shared faces.
                p=self.ref_lo[e]+np.clip(t,1e-10,1-1e-10)/self.n
                singular.append(np.linalg.svd(self.jacobian(p),compute_uv=False))
        sv=np.array(singular)
        sigma_lower=1/(math.sqrt(3)*self.alpha)
        return {"model":self.model,"grid":self.n,"q_base_exact":str(self.q_exact),
            "alpha_inf_exact":str(self.alpha_exact),"legacy_q_near_identity_upper":qnear,
            "cellwise_q_near_identity_upper":qcell,
            "legacy_q_gate_available":qnear<1,"global_injectivity_proven":True,
            "sigma_min_global_lower_2":sigma_lower,
            "sigma_min_sampled":float(sv[:,-1].min()),
            "condition_number_sampled_max":float((sv[:,0]/sv[:,-1]).max()),
            "condition_number_global_upper":float(np.max(np.linalg.norm(np.maximum(abs(Jlo),abs(Jhi)),axis=(1,2))))/sigma_lower,
            "jacobian_variation_cell_Fro_upper":float(np.linalg.norm(Jhi-Jlo,axis=(1,2)).max()),
            "rotation_degrees":2*math.degrees(math.atan(self.model["rotation_t"])),
            "proof":"globally invertible affine composition of X+amplitude*u(clamp X); q_base<1; never determinant-only",
            "sampling_role":"singular/condition samples descriptive; injectivity and whole-cell bounds do not rely on them"}
