"""Saved-contour analysis with adaptive, complete segment-neighbor search.

Primary candidate-12 estimates remain in metrics.csv. This independent analysis
checks the neighbor-search approximation without rerunning inverse/FE work.
"""
import json,time
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree
from core import ROOT

class PolylineDistance:
    def __init__(self,curves):
        self.a=np.concatenate([c[:-1] for c in curves]);self.b=np.concatenate([c[1:] for c in curves])
        self.d=self.b-self.a;self.length2=np.sum(self.d*self.d,axis=1)
        self.half=float(np.sqrt(self.length2).max()/2)
        self.tree=cKDTree((self.a+self.b)/2)
    def query(self,points):
        output=[]
        for p in np.array_split(points,max(1,len(points)//3000)):
            best=np.full(len(p),np.inf);pending=np.arange(len(p));k=min(12,len(self.a))
            while len(pending):
                distances,ids=self.tree.query(p[pending],k=k)
                if k==1:distances=distances[:,None];ids=ids[:,None]
                a=self.a[ids];d=self.d[ids];rel=p[pending,None,:]-a
                t=np.clip(np.einsum('nki,nki->nk',rel,d)/np.maximum(self.length2[ids],1e-300),0,1)
                best[pending]=np.linalg.norm(rel-t[:,:,None]*d,axis=2).min(axis=1)
                # Any unqueried segment midpoint is at least distances[:,-1]
                # away. Its segment cannot improve best if that lower bound
                # exceeds best plus the largest half-segment length.
                resolved=(distances[:,-1]>best[pending]+self.half+1e-12)|(k==len(self.a))
                pending=pending[~resolved];k=min(k*2,len(self.a))
            output.append(best)
        return np.concatenate(output)

def metric(curves,ref):
    if not curves or not ref:return dict(contour_to_reference_max=None,reference_to_contour_max=None,hausdorff_sampled=None)
    a=np.concatenate(curves+[(c[:-1]+c[1:])/2 for c in curves]);b=np.concatenate(ref)
    da=PolylineDistance(ref).query(a);db=PolylineDistance(curves).query(b)
    return dict(contour_to_reference_max=float(da.max()),reference_to_contour_max=float(db.max()),hausdorff_sampled=float(max(da.max(),db.max())))

def main():
    out=ROOT/'results';assert (out/'COMPLETION.json').exists()
    data=pd.read_csv(out/'metrics.csv');records=[];cache={};start=time.monotonic()
    max_delta=0.;brute_gap=0.;rng=np.random.default_rng(20261012)
    for i,row in data.iterrows():
        key=f"{row.field}_z{row.plane}_n{row.n}_r{row.radius}"
        # pandas can upcast n through iterrows; canonical filenames use ints.
        key=f"{row.field}_z{row.plane}_n{int(row.n)}_r{row.radius}"
        if key not in cache:
            cache={key:{k:[np.array(c) for c in v] for k,v in json.loads((out/'raw'/f'{key}_contours.json').read_text()).items()}}
        contours=cache[key];method='newton' if row.method=='newton' else f'{row.method}_k{int(row.order)}'
        cur=contours[method];ref=contours['reference'];nm=contours['newton']
        updated=metric(cur,ref);same=0. if row.method=='newton' else metric(cur,nm)['hausdorff_sampled']
        delta=abs(updated['hausdorff_sampled']-row.hausdorff_sampled) if updated['hausdorff_sampled'] is not None else 0.
        max_delta=max(max_delta,delta)
        record=row.to_dict();record['candidate12_hausdorff']=record['hausdorff_sampled']
        record['candidate12_same_grid']=record['same_grid_hausdorff'];record.update(updated)
        record['same_grid_hausdorff']=same;records.append(record)
        record['small_feature_to_contour_max']=float(PolylineDistance(cur).query(ref[-1]).max()) if cur else None
        # Independent exhaustive segment distances on deterministic random
        # points and farthest candidate-12 locations for selected datasets.
        if row.method=='newton' and int(row.n)==513:
            pdist=PolylineDistance(cur);pts=np.concatenate(ref)
            ids=np.r_[rng.integers(0,len(pts),8),np.argmax(pdist.query(pts))]
            for p in pts[ids]:
                rel=p-pdist.a;t=np.clip(np.sum(rel*pdist.d,axis=1)/np.maximum(pdist.length2,1e-300),0,1)
                brute=np.linalg.norm(rel-t[:,None]*pdist.d,axis=1).min()
                brute_gap=max(brute_gap,abs(float(brute)-pdist.query(p[None])[0]))
        if i%64==0:print('geometry rows',i+1,'elapsed',round(time.monotonic()-start,1),flush=True)
    pd.DataFrame(records).to_csv(out/'geometry_metrics.csv',index=False)
    (out/'geometry_search_validation.json').write_text(json.dumps(dict(rows=len(records),max_primary_estimator_change=max_delta,
        exhaustive_check_max_gap=brute_gap,method='adaptive midpoint search with maximum half-segment bound',
        finite_sample_metric_not_continuous_Hausdorff_certificate=True),indent=2)+'\n')
    print('geometry analysis complete',len(records),max_delta,brute_gap,flush=True)

if __name__=='__main__':main()
