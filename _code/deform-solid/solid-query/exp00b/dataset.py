"""Compact mechanism-based cases. Outer clearance is exact; hole clearance nominal."""
from fractions import Fraction as F
import copy
import math
import numpy as np
from common import Box,Solid
import oracle


def directed(value,up):
    v=float(value)
    if (F(v)<value and up) or (F(v)>value and not up):
        v=np.nextafter(v,math.inf if up else -math.inf)
    return float(v)


def make(model,seed=20261009):
    records=[]
    support_image,support_x=oracle.support(model)
    def record(group,x,delta,ratio=None,detail="",lo=None,hi=None):
        x=tuple(F(float(v)) for v in x)
        image=oracle.forward(model,x)
        if lo is None:
            center=np.array(list(map(float,image)))
            lo,hi=center-delta/2,center+delta/2
        rec={"id":f"{model['name']}-{len(records):03d}","model":model["name"],"group":group,
             "lo":list(map(float,lo)),"hi":list(map(float,hi)),"delta":delta,
             "delta_over_h4":delta*4,"clearance_ratio_nominal":ratio,
             "reference_seed":[str(v) for v in x],"detail":detail,"tau":0.,"decision_model":"exact_closed_query"}
        records.append(rec)
        return rec
    for delta in (1/128,1/1024,1/8192):
        for ratio in (-1/32,1/32,1/1024):
            lo=np.array([float(v)-delta/2 for v in support_image])
            hi=np.array([float(v)+delta/2 for v in support_image])
            lo[0]=directed(support_image[0]+F(delta)*F(ratio),True)
            hi[0]=lo[0]+delta
            rec=record("outer_clearance",support_x,delta,ratio,"spatial support-plane signed clearance",lo,hi)
            rec.update(support_point=[str(v) for v in support_x],support_value=str(support_image[0]),
                       clearance_exact=str(F(lo[0])-support_image[0]),
                       clearance_over_delta_actual=float((F(lo[0])-support_image[0])/F(delta)))
    for ratio in (-1/2**24,1/2**24):
        delta=1/8192
        lo=np.array([float(v)-delta/2 for v in support_image]);hi=lo+delta
        lo[0]=directed(support_image[0]+F(delta)*F(ratio),True);hi[0]=lo[0]+delta
        rec=record("outer_numerical_floor",support_x,delta,ratio,"clearance about 7e-12, near numerical guard",lo,hi)
        rec.update(support_point=[str(v) for v in support_x],support_value=str(support_image[0]),
                   clearance_exact=str(F(lo[0])-support_image[0]),clearance_over_delta_actual=float((F(lo[0])-support_image[0])/F(delta)))
    cx,cy,r=Solid().holes[0]
    for delta in (1/1024,1/8192):
        for ratio in (-1/8,1/8,1/1024):
            # This ratio describes an IDEAL reference box's right-face gap,
            # not the actual curved deformed-query clearance. Truth is oracle-only.
            x=(cx+r-delta/2-ratio*delta,cy,.5)
            record("hole_clearance",x,delta,ratio,"reference-box nominal gap; spatial truth independently checked")
    for x in ((11/32,.5,.5),(239/256,11/16,.5)):
        record("thin_wall",x,1/2048,None,"two different 1/128 reference walls")
    for x,location in [((.5,.625,.375),"face"),((.5,.5,.375),"edge"),((.5,.5,.5),"vertex")]:
        record("interface_"+location,x,1/8192,None,"center on reference FE "+location)
    for x in ((.15,.15,.4),(.8,.8,.6)):
        record("bulk",x,1/256,None,"material interior")
    record("singleton_interior",(.5,.625,.375),0,None,"closed singleton; no strict query interior exists")
    if model["rotation_t"] in (0,1):
        for x in ((1/16,.25,.5),(5/16+7/256,.5,.5)):
            rec=record("exact_contact",x,0,None,"exact dyadic outer/hole singleton contact")
            rec["exact_contact"]=True
    # Full-dimensional tangent support query only when exactly representable.
    if F(float(support_image[0]))==support_image[0]:
        delta=1/1024
        lo=np.array([float(v)-delta/2 for v in support_image]);hi=lo+delta
        lo[0]=float(support_image[0]);hi[0]=lo[0]+delta
        rec=record("exact_contact",support_x,delta,0.,"positive-volume box touches an exact support plane",lo,hi)
        rec.update(support_point=[str(v) for v in support_x],support_value=str(support_image[0]),
                   clearance_exact="0",clearance_over_delta_actual=0.,exact_contact=True)
    # Full-image broad phase should handle this with no inverse solve.
    rec=record("outside_far",support_x,1/128,None,"beyond entire FE image, not just solid support")
    rec["lo"][0]=2.;rec["hi"][0]=2.+1/128
    rec.update(support_point=[str(v) for v in support_x],support_value=str(support_image[0]))
    order=np.random.default_rng(seed).permutation(len(records))
    return [records[i] for i in order]


def box(record):
    return Box(record["lo"],record["hi"])


def dilated(rec,tau):
    new=copy.deepcopy(rec)
    new["id"]=rec["id"]+f"-tau{tau:.9g}"
    new["original_id"]=rec["id"]
    new["lo"]=[float(v-tau) for v in rec["lo"]]
    new["hi"]=[float(v+tau) for v in rec["hi"]]
    new["tau"]=tau
    new["decision_model"]="closed_query_dilated_in_spatial_Linf"
    if rec.get("support_value"):
        c=F(new["lo"][0])-F(rec["support_value"])
        new["clearance_exact"]=str(c)
        new["clearance_over_delta_actual"]=float(c/F(rec["delta"]))
    return new
