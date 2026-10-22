"""Q1 nodal field, double-double Newton, and independently optimized tensor norms."""
import itertools
import numpy as np
from scipy.optimize import minimize
from prepare import sphere

class DD:
 """Unevaluated pair of IEEE binary64 numbers; error-free sum/product kernels."""
 __array_priority__=1000
 def __init__(self,h,l=0.):self.h=np.asarray(h,dtype=float);self.l=np.broadcast_to(np.asarray(l,dtype=float),self.h.shape)
 def __getitem__(self,k):return DD(self.h[k],self.l[k])
 def __add__(self,b):
  b=asdd(b);s=self.h+b.h;v=s-self.h;e=(self.h-(s-v))+(b.h-v)+self.l+b.l;h=s+e;return DD(h,e-(h-s))
 __radd__=__add__
 def __neg__(self):return DD(-self.h,-self.l)
 def __sub__(self,b):return self+-asdd(b)
 def __rsub__(self,b):return asdd(b)+-self
 def __mul__(self,b):
  b=asdd(b);p=self.h*b.h;c=134217729.*self.h;ah=c-(c-self.h);al=self.h-ah;c=134217729.*b.h;bh=c-(c-b.h);bl=b.h-bh
  e=((ah*bh-p)+ah*bl+al*bh)+al*bl+self.h*b.l+self.l*b.h+self.l*b.l;h=p+e;return DD(h,e-(h-p))
 __rmul__=__mul__
 def __truediv__(self,b):
  b=asdd(b);q=self.h/b.h;r=self-b*q;q2=(r.h+r.l)/b.h;return DD(q)+q2
 def val(self):return self.h+self.l
def asdd(a):return a if isinstance(a,DD) else DD(a)
def stack(xs,axis=-1):return DD(np.stack([x.h for x in xs],axis=axis),np.stack([x.l for x in xs],axis=axis))
def matvec(a,v):return stack([sum((a[i,j]*v[...,j] for j in range(3)),DD(np.zeros(v.h.shape[:-1]))) for i in range(3)])
def solve(a,b):
 ai=np.linalg.inv(a.val());x=DD(np.einsum('ij,...j->...i',ai,b.val()))
 for _ in range(2):x=x+DD(np.einsum('ij,...j->...i',ai,(b-matvec(a,x)).val()))
 return x
def coefficients(nodal,half,local):
 c=[]
 for mask in range(8):
  weights=np.prod(local[:,[k for k in range(3) if mask&(1<<k)]],axis=1)/8
  v=sum((DD(nodal[a])*weights[a] for a in range(8)),DD(np.zeros(3)))
  for k in range(3):
   if mask&(1<<k):v=v/half[k]
  c.append(v)
 return c
def tensors(c):
 G=np.column_stack([c[1<<k].val() for k in range(3)]);H=np.zeros((3,3,3));T=np.zeros((3,3,3,3))
 for j,k in itertools.permutations(range(3),2):H[:,j,k]=c[(1<<j)|(1<<k)].val()
 for j,k,l in itertools.permutations(range(3)):T[:,j,k,l]=c[7].val()
 return G,H,T
def Fdd(c):return stack([stack([c[1<<j][i]+float(i==j) for j in range(3)]) for i in range(3)],axis=0)
def h(c,a,b):
 return sum((c[(1<<j)|(1<<k)]*(a[...,j]*b[...,k]+a[...,k]*b[...,j])[...,None] for j,k in ((0,1),(0,2),(1,2))),DD(np.zeros(a.h.shape)))
def tr(c,a,b,d):
 s=sum((a[...,j]*b[...,k]*d[...,l] for j,k,l in itertools.permutations(range(3))),DD(np.zeros(a.h.shape[:-1])))
 return c[7]*s[...,None]
def forward(c,y):
 return y+sum((c[mask]*prod_coord(y,mask)[...,None] for mask in range(1,8)),DD(np.zeros(y.h.shape)))
def prod_coord(y,mask):
 v=DD(np.ones(y.h.shape[:-1]))
 for j in range(3):
  if mask&(1<<j):v=v*y[...,j]
 return v
def jacobian(c,y):
 cv=[v.val() for v in c];v=y.val();J=np.broadcast_to(np.eye(3),v.shape[:-1]+(3,3)).copy()
 for j in range(3):
  for mask in range(1,8):
   if mask&(1<<j):
    fac=np.ones(v.shape[:-1])
    for k in range(3):
     if k!=j and mask&(1<<k):fac*=v[...,k]
    J[..., :,j]+=fac[...,None]*cv[mask]
 return J
def rays(c,d):
 F=Fdd(c);p1=solve(F,DD(d));p2=solve(F,-h(c,p1,p1)/2)
 p3=solve(F,-h(c,p1,p2)-tr(c,p1,p1,p1)/6)
 p4=solve(F,-h(c,p1,p3)-h(c,p2,p2)/2-tr(c,p1,p1,p2)/2)
 return [p1,p2,p3,p4]
def inverse(c,target,initial,he):
 y=initial;mindet=np.full(target.h.shape[:-1],np.inf)
 for it in range(12):
  J=jacobian(c,y);mindet=np.minimum(mindet,np.linalg.det(J));r=forward(c,y)-target
  if np.max(np.linalg.norm(r.val(),axis=-1))/he<1e-29:break
  step=np.linalg.solve(J,r.val()[...,None])[...,0];y=y-DD(step)
 res=np.linalg.norm((forward(c,y)-target).val(),axis=-1)/he
 return y,res,mindet,it+1
def full_jet(F,H,T):
 # General full-tensor formula from Exp2D, forward provider replaced by explicit jets.
 A=np.linalg.inv(F);B=np.zeros((3,3,3));C=np.zeros((3,3,3,3))
 h2=lambda a,b:np.einsum('ijk,j,k->i',H,a,b)
 for i,j in itertools.product(range(3),repeat=2):
  ai,aj=A[:,i],A[:,j];B[:,i,j]=-A@h2(ai,aj)
  for k in range(3):
   ak=A[:,k];third=np.einsum('iabc,a,b,c->i',T,ai,aj,ak)
   C[:,i,j,k]=A@(-third+h2(A@h2(ai,aj),ak)+h2(A@h2(ai,ak),aj)+h2(A@h2(aj,ak),ai))
 return A,B,C

SEEDS=sphere(4096)
def opnorm(H,T):
 scale=np.linalg.norm(H)
 if scale==0:return 0.,float(np.linalg.norm(T[:,0,1,2])*2/np.sqrt(3)),np.array([1.,0,0]),0.
 Q=H/scale
 def fun(a):
  v=np.einsum('ijk,j,k->i',Q,a,a);dv=2*np.einsum('ijk,k->ij',Q,a);return -v@v,-2*dv.T@v
 vals=np.linalg.norm(np.einsum('ijk,nj,nk->ni',Q,SEEDS,SEEDS),axis=1)
 best=(-1,None)
 for ind in np.argsort(vals)[-16:]:
  opt=minimize(fun,SEEDS[ind],jac=True,method='SLSQP',constraints={'type':'eq','fun':lambda a:a@a-1,'jac':lambda a:2*a},options={'ftol':1e-14,'maxiter':150})
  a=opt.x/np.linalg.norm(opt.x);v=np.linalg.norm(np.einsum('ijk,j,k->i',Q,a,a))
  if v>best[0]:best=(v,a)
 # Independent multilinear alternating maximization, no diagonal constraint.
 a=sphere(256);b=np.roll(a,71,axis=0).copy()
 for _ in range(100):
  w=np.einsum('ijk,nj,nk->ni',Q,a,b);w/=np.maximum(np.linalg.norm(w,axis=1)[:,None],1e-300)
  a=np.einsum('ijk,ni,nk->nj',Q,w,b);a/=np.maximum(np.linalg.norm(a,axis=1)[:,None],1e-300)
  b=np.einsum('ijk,ni,nj->nk',Q,w,a);b/=np.maximum(np.linalg.norm(b,axis=1)[:,None],1e-300)
 av=np.linalg.norm(np.einsum('ijk,nj,nk->ni',Q,a,b),axis=1);ref=av.max()
 def multi(x):
  aa,bb=x[:3],x[3:];v=np.einsum('ijk,j,k->i',Q,aa,bb)
  da=np.einsum('ijk,k->ij',Q,bb);db=np.einsum('ijk,j->ik',Q,aa)
  return -v@v,np.r_[-2*da.T@v,-2*db.T@v]
 for ind in np.argsort(av)[-4:]:
  opt=minimize(multi,np.r_[a[ind],b[ind]],jac=True,method='SLSQP',constraints=[{'type':'eq','fun':lambda x:x[:3]@x[:3]-1,'jac':lambda x:np.r_[2*x[:3],np.zeros(3)]},{'type':'eq','fun':lambda x:x[3:]@x[3:]-1,'jac':lambda x:np.r_[np.zeros(3),2*x[3:]]}],options={'ftol':1e-14,'maxiter':300})
  aa=opt.x[:3]/np.linalg.norm(opt.x[:3]);bb=opt.x[3:]/np.linalg.norm(opt.x[3:]);ref=max(ref,np.linalg.norm(np.einsum('ijk,j,k->i',Q,aa,bb)))
 assert abs(best[0]-ref)<1e-8, (best[0],ref)
 return max(best[0],ref)*scale,float(np.linalg.norm(T[:,0,1,2])*2/np.sqrt(3)),best[1],abs(best[0]-ref)/best[0]
