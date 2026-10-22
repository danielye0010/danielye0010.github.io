"""Conventional median-split AABB BVH; closed overlap and identical scan hits."""
import numpy as np


class Index:
    def __init__(self,lo,hi,leaf_size=8):
        self.lo,self.hi=lo,hi
        self.nodes=[]
        def build(ids):
            node=len(self.nodes)
            a,b=lo[ids].min(axis=0),hi[ids].max(axis=0)
            self.nodes.append(None)
            if len(ids)<=leaf_size:
                self.nodes[node]=(a,b,-1,-1,ids)
            else:
                centers=(lo[ids]+hi[ids])/2
                axis=int(np.argmax(np.ptp(centers,axis=0)))
                order=ids[np.argsort(centers[:,axis],kind="stable")]
                mid=len(ids)//2
                left,right=build(order[:mid]),build(order[mid:])
                self.nodes[node]=(a,b,left,right,None)
            return node
        build(np.arange(len(lo)))
        self.storage_bytes=sum(a.nbytes+b.nbytes+(ids.nbytes if ids is not None else 16) for a,b,l,r,ids in self.nodes)

    def query(self,box,stats):
        stack=[0]
        hits=[]
        while stack:
            a,b,l,r,ids=self.nodes[stack.pop()]
            stats.bvh_nodes+=1
            if np.any(b<box.lo) or np.any(a>box.hi):
                continue
            if ids is not None:
                stats.cell_tests+=len(ids)
                mask=np.all(self.hi[ids]>=box.lo,axis=1)&np.all(self.lo[ids]<=box.hi,axis=1)
                hits.extend(ids[mask])
            else:
                stack.extend((r,l))
        return np.array(sorted(hits),dtype=int)


def candidates(field,box,stats,mode="bvh"):
    stats.localizations+=1
    if mode=="bvh":
        return field.index.query(box,stats)
    stats.cell_tests+=len(field.image_lo)
    return np.flatnonzero(np.all(field.image_hi>=box.lo,axis=1)&np.all(field.image_lo<=box.hi,axis=1))
