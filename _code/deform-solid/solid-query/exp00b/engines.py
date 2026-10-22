"""Indexed A, original scalar-bound B, and scalar-arithmetic implementation C."""
from dataclasses import dataclass,asdict
from collections import deque
from time import perf_counter
import numpy as np
from common import Box,Solid,OldStats,newton
from bvh import candidates
import oracle


@dataclass
class Stats(OldStats):
    max_depth: int=0
    bvh_nodes: int=0
    cell_tests: int=0
    localizations: int=0
    point_inverse_failures: int=0
    mixed_enclosures: int=0
    enclosure_full: int=0
    max_enclosure_ratio: float=0.
    localization_seconds: float=0.
    inverse_seconds: float=0.
    enclosure_seconds: float=0.
    geometry_seconds: float=0.
    subdivision_seconds: float=0.


class Engine:
    def __init__(self,field,config,method="B",index="bvh"):
        self.field,self.cfg,self.method,self.index=field,config,method,index
        self.solid=Solid()

    def locate(self,box,stats):
        start=perf_counter()
        ids=candidates(self.field,box,stats,self.index)
        stats.localization_seconds+=perf_counter()-start
        return ids

    def point_witness(self,x,query,stats):
        if not self.solid.interior(x,self.field.guard):
            return False
        y=self.field.evaluate(x,stats)
        if np.all(y>query.lo+self.field.guard) and np.all(y<query.hi-self.field.guard):
            return True
        # Closed membership is allowed. Borderline/singleton equality needs
        # exact rational forward evaluation, not a floating equality shortcut.
        if np.all(y>=query.lo) and np.all(y<=query.hi):
            from fractions import Fraction as F
            return oracle.valid_witness(self.field.model,oracle.intervals(query),tuple(F(v) for v in x))
        return False

    def result(self,status,stats,cause,witness=None,kind=None,spatial=None):
        return {"status":status,"cause":cause,"witness":None if witness is None else witness.tolist(),
                "witness_kind":kind,"spatial_witness":None if spatial is None else spatial.tolist(),"stats":asdict(stats)}

    def query(self,query):
        f,stats=self.field,Stats()
        ids=self.locate(query,stats)
        stats.candidates=len(ids)
        if not len(ids):
            return self.result("DISJOINT",stats,"cell_images_exclude_query")
        if self.method=="A":
            start=perf_counter()
            dist=np.sum(((f.image_lo[ids]+f.image_hi[ids])/2-query.center)**2,axis=1)
            ids=ids[np.argsort(dist,kind="stable")]
            stats.localization_seconds+=perf_counter()-start
            initial=[]
            for e in ids:
                lo,hi=f.ref_lo[e],f.ref_hi[e]
                if self.cfg.get("clip_outer_body",True):
                    lo,hi=np.maximum(lo,self.solid.lo),np.minimum(hi,self.solid.hi)
                if np.all(lo<=hi):
                    initial.append((Box(lo,hi),0,int(e)))
            pending=deque(initial)
        else:
            pending=deque([(query,0,None)])
        terminal_reasons=set()
        while pending and stats.nodes<self.cfg["max_nodes"]:
            stats.peak_pending=max(stats.peak_pending,len(pending))
            region,depth,context=pending.popleft()
            stats.nodes+=1;stats.max_depth=max(stats.max_depth,depth)
            if self.method=="A":
                t=perf_counter()
                state=self.solid.classify(region,f.guard)
                stats.geometry_seconds+=perf_counter()-t
                if state=="EMPTY":
                    stats.empty_geometry+=1
                    continue
                t=perf_counter()
                bound=f.cell_bounds(context,region,stats)
                excluded=not bound.overlaps(query)
                stats.enclosure_seconds+=perf_counter()-t
                if excluded:
                    stats.empty_spatial+=1
                    continue
                x=region.center
            else:
                if not len(self.locate(region,stats)):
                    stats.empty_spatial+=1
                    continue
                t=perf_counter()
                x,residual=newton(f,region.center,stats,context)
                stats.inverse_seconds+=perf_counter()-t
                if residual>2e-14:
                    stats.point_inverse_failures+=1
                t=perf_counter()
                radius=f.alpha*(region.width.max()/2+residual+f.guard)+f.guard
                point_radius=f.alpha*(residual+f.guard)+f.guard
                ref=Box(x-radius,x+radius)
                point_ref=Box(x-point_radius,x+point_radius)
                stats.max_enclosure_ratio=max(stats.max_enclosure_ratio,2*radius/max(float(region.width.max()),1e-300))
                stats.enclosure_seconds+=perf_counter()-t
                t=perf_counter()
                state=self.solid.classify(ref,f.guard)
                point_state=self.solid.classify(point_ref,f.guard)
                stats.geometry_seconds+=perf_counter()-t
                if state=="EMPTY":
                    stats.empty_geometry+=1
                    continue
                if state=="FULL":
                    stats.enclosure_full+=1
                else:
                    stats.mixed_enclosures+=1
                if point_state=="FULL":
                    # c is IN the CLOSED query and global inverse existence is
                    # proven. The inverse root is in strict material interior.
                    return self.result("INTERSECTS",stats,"posterior_closed_center_witness",x,"posterior_center_root",region.center)
            t=perf_counter()
            witness=self.point_witness(x,query,stats)
            stats.geometry_seconds+=perf_counter()-t
            if witness:
                return self.result("INTERSECTS",stats,"closed_forward_witness",x,"forward_point")
            t=perf_counter()
            children=region.split()
            if depth>=self.cfg["max_depth"]:
                terminal_reasons.add("depth_limit")
            elif region.width.max()<=self.cfg["min_width"] or children is None:
                terminal_reasons.add("singleton_or_width_floor")
            else:
                if self.method=="A":
                    pending.extend((r,depth+1,context) for r in children)
                else:
                    pending.extend((r,depth+1,x) for r in children)
                stats.splits+=1
            stats.subdivision_seconds+=perf_counter()-t
        if pending:
            return self.result("UNRESOLVED",stats,"node_budget")
        if terminal_reasons:
            return self.result("UNRESOLVED",stats,"+".join(sorted(terminal_reasons)))
        return self.result("DISJOINT",stats,"entire_region_excluded")
