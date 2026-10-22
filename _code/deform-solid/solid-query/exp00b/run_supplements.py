"""Targeted refinement, changed-task tolerance study, and implementation controls."""
import argparse
import csv
import json
from pathlib import Path
from time import perf_counter
import tracemalloc
import numpy as np
from common import ROOT,configuration,write_json,freeze_parent
from fields import Deformation
from engines import Engine,Stats
from bvh import candidates
from run import freeze,execute,write_csv
from qualify import read_csv
import dataset,oracle


def refinement(out):
    cfg=configuration()
    coarse=read_csv(ROOT/"results/coarse/timings.csv")
    models=[]
    triggers=[]
    for name in ("nonlinear_high","nonlinear_cond8"):
        rows=[r for r in coarse if r["model"]==name and r["grid"]=="4" and r["method"]=="B" and
              r["budget"]=="2047" and r["group"] not in ("exact_contact","singleton_interior","outer_numerical_floor")]
        failed=sum(r["status"]=="UNRESOLVED" for r in rows)
        mean=float(np.mean([int(r["nodes"]) for r in rows]))
        triggers.append({"model":name,"regular_unresolved":failed,"mean_nodes":mean})
        if failed or mean>=16:
            base=next(m for m in cfg["models"] if m["name"]==name)
            if name=="nonlinear_high":
                models.extend([dict(base,name="nonlinear_qnear_33_16",amplitude=33/16),
                               dict(base,name="nonlinear_qnear_67_32",amplitude=67/32)])
            else:
                models.extend([dict(base,name="nonlinear_cond32",stretch_z=1/32),
                               dict(base,name="affine_cond32",amplitude=0,stretch_z=1/32)])
    if not models:
        raise SystemExit("no observed transition justifies refinement")
    selected=("outer_clearance","hole_clearance","thin_wall","interface_face","interface_edge","interface_vertex")
    queries=sum(([r for r in dataset.make(m,cfg["seed"]) if r["group"] in selected] for m in models),[])
    scenarios=[(m["name"],4) for m in models]
    freeze(out,{"phase":"refined","observed_triggers":triggers,"models":models,"selected_groups":selected,
                "scenarios":scenarios,"budgets":cfg["budgets"],"reason":"only conditioning/q-bound transitions; no new query algorithm"})
    execute(out,models,queries,scenarios,cfg["budgets"])


def tolerance(out):
    cfg=configuration()
    models=[m for m in cfg["models"] if m["name"] in ("nonlinear_mild","nonlinear_high","nonlinear_cond8")]
    queries=[]
    for m in models:
        chosen=[r for r in dataset.make(m,cfg["seed"]) if r["group"] in ("outer_numerical_floor","exact_contact")
                and r.get("support_point")]
        chosen+= [r for r in dataset.make(m,cfg["seed"]) if r["group"]=="outer_clearance" and r["delta"]==1/8192
                  and r["clearance_ratio_nominal"]==1/1024]
        for rec in chosen:
            queries.extend(dataset.dilated(rec,tau) for tau in cfg["tau_values"])
    freeze(out,{"phase":"tolerance","models":models,"tau_values":cfg["tau_values"],
                "semantic_model":"intersection of solid with separately specified CLOSED expanded query; never relabel original exact truth",
                "budgets":[2047],"rounding":"stored binary64 expanded endpoints define tested query; rational oracle uses those exact endpoints"})
    execute(out,models,queries,[(m["name"],4) for m in models],[2047])


def controls(out):
    cfg=configuration()
    model=next(m for m in cfg["models"] if m["name"]=="nonlinear_mild")
    original=dataset.make(model,cfg["seed"])
    groups=("outer_clearance","hole_clearance","thin_wall","interface_face","bulk")
    chosen=[next(r for r in original if r["group"]==g) for g in groups]
    freeze(out,{"phase":"controls","models":[model],"groups":groups,"repetitions":3,"budget":511,
                "query_counts":cfg["query_counts"],"index_modes":["scan","bvh"],
                "body_clip_modes":[False,True],"note":"same broad-phase hits, same inverse region algorithm; no method development"})
    rows=[];preprocessing=[];memory=[];localization=[]
    for n in (4,8):
        field=Deformation(model,n)
        # Lookup microbenchmark isolates broad phase on ALL query boxes.
        for repeat in range(3):
            for mode in ("scan","bvh"):
                stats=Stats(); t=perf_counter()
                found=[candidates(field,dataset.box(rec),stats,mode).tolist() for rec in original]
                elapsed=perf_counter()-t
                other=[candidates(field,dataset.box(rec),Stats(),"scan" if mode=="bvh" else "bvh").tolist() for rec in original]
                assert found==other
                localization.append({"grid":n,"index":mode,"repeat":repeat,"query_count":len(original),
                                     "seconds":elapsed,"cell_tests":stats.cell_tests,"bvh_nodes":stats.bvh_nodes,"hits_identical":True})
        for method in ("A","B","C"):
            for mode in ("scan","bvh"):
                for clip in ((False,True) if method=="A" else (True,)):
                    for repeat in range(3):
                        t=perf_counter();field=Deformation(model,n,fast=method=="C");prep=perf_counter()-t
                        preprocessing.append({"grid":n,"method":method,"index":mode,"clip":clip,"repeat":repeat,
                                              "seconds":prep,"bytes":field.storage_bytes})
                        engine=Engine(field,dict(cfg,max_nodes=511,clip_outer_body=clip),method,mode)
                        for rec in chosen:
                            box=dataset.box(rec);t=perf_counter();result=engine.query(box);elapsed=perf_counter()-t
                            assert oracle.verify_result(model,box,result) is not False
                            rows.append({"id":rec["id"],"grid":n,"method":method,"index":mode,"clip":clip,"repeat":repeat,
                                         "group":rec["group"],"seconds":elapsed,"status":result["status"],**result["stats"]})
                        if repeat==0:
                            rec=next(r for r in original if r["group"]=="hole_clearance")
                            tracemalloc.start();engine.query(dataset.box(rec));_,peak=tracemalloc.get_traced_memory();tracemalloc.stop()
                            memory.append({"grid":n,"method":method,"index":mode,"clip":clip,
                                           "persistent_array_index_bytes":field.storage_bytes,"tracked_query_peak_bytes":peak})
    write_csv(out/"timings.csv",rows)
    write_csv(out/"preprocessing.csv",preprocessing)
    write_csv(out/"memory.csv",memory)
    write_csv(out/"localization.csv",localization)
    batches=[]
    # Counts scale the SAME frozen regular workload, cycling without answer
    # caching. Exact contacts/numerical-floor stress excluded and disclosed.
    regular=[r for r in original if r["group"] not in ("exact_contact","singleton_interior","outer_numerical_floor")]
    for count in cfg["query_counts"]:
        for repeat in range(3):
            for method in ("A","B","C"):
                t=perf_counter();field=Deformation(model,4,fast=method=="C");prep=perf_counter()-t
                engine=Engine(field,dict(cfg,max_nodes=511),method,"bvh")
                batch=[dataset.box(regular[j%len(regular)]) for j in range(count)]
                t=perf_counter();results=[engine.query(box) for box in batch];elapsed=perf_counter()-t
                batches.append({"N":count,"repeat":repeat,"method":method,"preprocess_seconds":prep,
                                "query_seconds":elapsed,"total_seconds":prep+elapsed,"unresolved":sum(r["status"]=="UNRESOLVED" for r in results),
                                "nodes":sum(r["stats"]["nodes"] for r in results)})
        write_csv(out/"batches.csv",batches)
        print("Actual control batch N=",count,"complete",flush=True)
    write_json(out/"validation.json",{"control_rows":len(rows),"lookup_rows":len(localization),"batch_rows":len(batches),
              "parent_preserved":True,"purpose":"overhead/localization/body-clip controls; primary work metrics are elsewhere"})
    freeze_parent()


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("phase",choices=("refined","tolerance","controls"))
    parser.add_argument("--output",type=Path)
    args=parser.parse_args()
    out=(args.output or ROOT/"results"/args.phase).resolve()
    {"refined":refinement,"tolerance":tolerance,"controls":controls}[args.phase](out)
