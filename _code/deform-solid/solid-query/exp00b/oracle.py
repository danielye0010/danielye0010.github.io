"""Independent rational truth/checking: exact closed sets, no sampled disjointness."""
from fractions import Fraction as F
from itertools import product
import math
import numpy as np
from common import old_oracle as O
from fields import affine_exact

# Process-local precision change; no 00-A file or result is modified.
O.SCALE=2**60


def forward(model,x):
    amp=F(model["amplitude"])
    base=O.forward("nonlinear",x) if amp else x
    base=[x[i]+amp*(base[i]-x[i]) for i in range(3)]
    A,Ai,b=affine_exact(model)
    return tuple(b[i]+sum(A[i][j]*base[j] for j in range(3)) for i in range(3))


def closed_material(x):
    return (all(O.BODY_LO<=v<=O.BODY_HI for v in x) and
            all((x[0]-a)**2+(x[1]-b)**2>=r*r for a,b,r in O.HOLES))


def intervals(box):
    return tuple((F(float(a)),F(float(b))) for a,b in zip(box.lo,box.hi))


def transformed_rhs(model,query):
    A,Ai,b=affine_exact(model)
    shifted=[(a-b[i],c-b[i]) for i,(a,c) in enumerate(query)]
    result=[]
    for row in Ai:
        v=(F(0),F(0))
        for coeff,pair in zip(row,shifted):
            v=O.add(v,O.scale(pair,coeff))
        result.append(O.lattice(v))
    return tuple(result)


def inverse_box(model,query,iterations=180):
    rhs=transformed_rhs(model,query)
    amp=F(model["amplitude"])
    if not amp:
        return rhs
    u=[O.scale(v,amp) for v in O.u_interval("nonlinear",[(F(0),F(1))]*3)]
    current=tuple(O.lattice((a-v,b-w)) for (a,b),(w,v) in zip(rhs,u))
    for _ in range(iterations):
        u=[O.scale(v,amp) for v in O.u_interval("nonlinear",current)]
        new=tuple((max(a,O.lattice((c-v,d-w))[0]),min(b,O.lattice((c-v,d-w))[1]))
                  for (a,b),(c,d),(w,v) in zip(current,rhs,u))
        assert all(a<=b for a,b in new)
        if current==new:
            break
        current=new
    return current


def seed(model,spatial):
    # Analytic fixed point, independent of nodal interpolation/Jacobian/Newton.
    A,Ai,b=affine_exact(model)
    target=np.array([float(sum(Ai[i][j]*(spatial[j]-b[j]) for j in range(3))) for i in range(3)])
    x=target.copy()
    amp=float(model["amplitude"])
    for _ in range(200):
        f=[]
        for v in x:
            t=min(1.,max(0.,float(v)))
            k=min(int(4*t),3)
            f.append((0.,.75,1.,.25)[k]+(t-k/4)*(3.,1.,-3.,-1.)[k])
        a,c,d=f
        u=np.array([c*d/16+a*c/64,3*a*d/64-c*d/64,a*c/32+a*c*d/64])
        new=target-amp*u
        if np.max(abs(new-x))<1e-15:
            x=new
            break
        x=new
    return tuple(F(float(v)) for v in x)


def valid_witness(model,query,x,require_interior=True):
    if require_interior:
        if O.solid_classify(tuple((v,v) for v in x))!="FULL":
            return False
    elif not closed_material(x):
        return False
    image=forward(model,x)
    return all(a<=v<=b for (a,b),v in zip(query,image))


def support(model):
    # Exact extrema of each body-truncated Q1 cell occur at its vertices.
    coords=(O.BODY_LO,F(1,4),F(1,2),F(3,4),O.BODY_HI)
    best=None
    for point in product(coords,repeat=3):
        image=forward(model,point)
        if best is None or image[0]>best[0][0]:
            best=image,point
    assert closed_material(best[1]),"body extremum lies in removed geometry"
    return best


def classify(model,box,record=None,iterations=180,max_nodes=255):
    query=intervals(box)
    if record and record.get("support_point"):
        p=tuple(F(v) for v in record["support_point"])
        ymax=F(record["support_value"])
        assert forward(model,p)[0]==ymax and closed_material(p)
        if query[0][0]>ymax:
            return {"truth":"DISJOINT","proof":"exact Q1 body support plane excludes entire query",
                    "clearance_exact":str(query[0][0]-ymax),"nodes":0}
        if valid_witness(model,query,p,False):
            return {"truth":"INTERSECTS","proof":"exact closed-set support witness",
                    "witness":[str(v) for v in p],"nodes":0}
    # First look for independently checked INTERIOR witnesses. This is not
    # a disjointness test: every positive witness is evaluated exactly.
    if np.any(box.width>0):
        for weights in [(F(1,2),)*3]+list(product((F(1,4),F(3,4)),repeat=3)):
            target=tuple(a+(b-a)*t for (a,b),t in zip(query,weights))
            x=seed(model,target)
            if valid_witness(model,query,x):
                return {"truth":"INTERSECTS","proof":"independent exact interior witness",
                        "witness":[str(v) for v in x],"nodes":0}
    stack=[(query,0)]
    proofs=[]
    nodes=0
    terminal=False
    while stack and nodes<max_nodes:
        q,depth=stack.pop()
        nodes+=1
        inv=inverse_box(model,q,iterations)
        state=O.solid_classify(inv)
        if state=="EMPTY":
            proofs.append({"query":[[str(v) for v in p] for p in q],
                           "preimage":[[str(v) for v in p] for p in inv]})
            continue
        if state=="FULL":
            return {"truth":"INTERSECTS","proof":"global existence and exact material-interior inverse enclosure",
                    "spatial_witness":[str((a+b)/2) for a,b in q],"preimage":[[str(v) for v in p] for p in inv],"nodes":nodes}
        if all(a==b for a,b in q):
            terminal=True
            continue
        center=tuple((a+b)/2 for a,b in q)
        x=seed(model,center)
        if valid_witness(model,query,x):
            return {"truth":"INTERSECTS","proof":"subdivision exact interior witness","witness":[str(v) for v in x],"nodes":nodes}
        axis=max(range(3),key=lambda k:q[k][1]-q[k][0])
        a,b=q[axis]
        if depth>=36 or b-a<=F(1,2**40):
            terminal=True
            continue
        m=(a+b)/2
        left,right=list(q),list(q)
        left[axis],right[axis]=(a,m),(m,b)
        stack.extend(((tuple(right),depth+1),(tuple(left),depth+1)))
    if not stack and not terminal:
        return {"truth":"DISJOINT","proof":"exact inverse fixed-point interval exclusion cover","cover":proofs,"nodes":nodes}
    if record and record.get("exact_contact"):
        x=tuple(F(v) for v in record["reference_seed"])
        if valid_witness(model,query,x,False):
            return {"truth":"INTERSECTS","proof":"exact singleton boundary contact","nodes":nodes}
    return {"truth":"UNKNOWN","proof":"independent oracle budget/precision limit","nodes":nodes}


def verify_result(model,box,result):
    if result["status"]!="INTERSECTS":
        return None
    query=intervals(box)
    if result["witness_kind"]=="forward_point":
        return valid_witness(model,query,tuple(F(v) for v in result["witness"]))
    # Independently recompute the EXACT residual of the claimed center-root
    # certificate, rather than trusting floating radius or stored booleans.
    x=tuple(F(v) for v in result["witness"])
    c=tuple(F(v) for v in result["spatial_witness"])
    if not all(a<=v<=b for (a,b),v in zip(query,c)):
        return False
    y=forward(model,x)
    e=max(abs(v-w) for v,w in zip(y,c))
    A,Ai,b=affine_exact(model)
    alpha=max(sum(abs(v) for v in row) for row in Ai)/(1-F(model["amplitude"])*F(15,32))
    ref=tuple((v-alpha*e,v+alpha*e) for v in x)
    return O.solid_classify(ref)=="FULL"
