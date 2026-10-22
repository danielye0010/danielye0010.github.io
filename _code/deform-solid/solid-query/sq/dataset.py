"""Deterministic query generation; no answer labels used by either baseline."""
import json
from pathlib import Path
import numpy as np
from .field import Field
from .geometry import Box, Solid


def make_queries(kind, seed=20261009):
    rng = np.random.default_rng(seed)
    field, solid = Field(kind,4), Solid()
    records = []

    def append(group,x,half,detail):
        x,half = np.asarray(x,float),np.broadcast_to(half,(3,)).copy()
        center = field.evaluate(x)
        records.append({"id":f"{kind}-{len(records):03d}","map":kind,"group":group,
            "reference_seed":x.tolist(),"lo":(center-half).tolist(),"hi":(center+half).tolist(),"detail":detail})

    for j in range(6):
        z = (j+2)/10
        append("outside_far",[-.125 if j%2==0 else 1.125,.3,z],.025,"outside grid image")
        append("bulk",[.15+.1*(j%3),.2+.1*(j//3),z],.006,"clear material")
        cx,cy,r = solid.holes[j%4]
        append("hole_core",[cx,cy,z],[r/8,r/8,.02],"anisotropic cylinder interior")
        epsilon = [1/8,1/64,1/512][j//2]
        append("hole_near_wall",[cx+r*(1-epsilon),cy,z],r*epsilon/16,"strict void, shrinking clearance")
        append("hole_crossing",[cx+r,cy,z],r/8,"crosses cylindrical wall")
        thin_x,thin_y = (11/32,1/2) if j%2==0 else (239/256,11/16)
        append("thin_wall",[thin_x,thin_y,z],1/2048,"wall thickness 1/128")
        clearance = [1/1024,1/16384,1/262144][j//2]
        append("outer_near",[1/16+(-1 if j%2 else 1)*clearance,.25,z],clearance/8,
               "alternating interior/exterior small clearance")
        append("interface",[.25*(1+j%3),.625,.375],1/(64*2**(j%3)),"query crosses FE face")
        append("large_mixed",[cx,cy,z],.04+.02*(j%3),"hole-centered box reaches material")
    for x,description in [([1/16,.25,.5],"outer point contact"),
                           ([5/16+7/256,1/2,.5],"hole point contact"),
                           ([.5,.625,.375],"interior zero-volume query")]:
        append("degenerate",x,0.,description)
    for _ in range(7):
        x = rng.uniform(.025,.975,3)
        append("random",x,2.**(-int(rng.integers(4,12))),"seeded spatial query")
    order = rng.permutation(len(records))
    return [records[i] for i in order]


def box_from_record(record):
    return Box(record["lo"],record["hi"])


def write_dataset(path,seed):
    records = sum((make_queries(kind,seed) for kind in ("identity","affine","nonlinear")),[])
    payload = {"schema":1,"seed":seed,"geometry":Solid().as_dict(),"queries":records,
               "coordinates":"JSON binary64 endpoints interpreted exactly by independent Fraction oracle"}
    Path(path).write_text(json.dumps(payload,indent=2)+"\n")
    return records
