"""Frozen compact coarse sweep; controlled refinement is selected AFTER inspection."""
import argparse
import csv
import json
from pathlib import Path
from time import perf_counter
import tracemalloc
import unittest
import numpy as np
from common import ROOT,PARENT,configuration,freeze_parent,parent_inventory,sha,write_json
from fields import Deformation
from engines import Engine
import dataset
import oracle


def write_csv(path,rows,fields=None):
    with path.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=fields or list(rows[0]))
        w.writeheader();w.writerows(rows)


def freeze(out,plan):
    import shutil
    if out.exists() and any(out.iterdir()):
        raise SystemExit("choose a fresh output directory")
    out.mkdir(parents=True,exist_ok=True)
    freeze_parent()
    files=sorted([ROOT/"config.json",ROOT/"AUDIT_00A.md",*ROOT.glob("*.py"),*ROOT.glob("tests/*.py")])
    payload={"plan":plan,"config":configuration(),"source_sha256":{p.relative_to(ROOT).as_posix():sha(p) for p in files},
             "parent_preservation_sha256":sha(ROOT/"PARENT_PRESERVATION.json")}
    write_json(out/"PRE_RUN_FREEZE.json",payload)
    for p in files:
        dest=out/"source"/p.relative_to(ROOT)
        dest.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(p,dest)


def mechanism(result,rec,truth,method):
    if result["status"]!="UNRESOLVED":
        return "resolved"
    if rec.get("exact_contact"):
        return "exact_contact"
    if rec["group"]=="singleton_interior":
        return "singleton_witness_availability"
    if result["stats"]["point_inverse_failures"] and result["stats"]["max_residual"]>1e-10:
        return "point_solve_tolerance_failed"
    if "floor" in result["cause"]:
        return "numerical_or_spatial_floor"
    if "depth" in result["cause"]:
        return "depth_limit"
    if method=="A":
        return "forward_witness_search" if truth=="INTERSECTS" else "forward_exclusion_search"
    return "inverse_region_subdivision"


def execute(out,models,queries,scenarios,budgets,config=None,index="bvh"):
    cfg=config or configuration()
    write_json(out/"queries.json",{"models":models,"queries":queries,"ground_truth":"closed-set predicate on exact binary64 endpoints"})
    model_by={m["name"]:m for m in models}
    answers={}
    with (out/"oracle.jsonl").open("w",encoding="utf-8") as stream:
        for rec in queries:
            start=perf_counter()
            ans=oracle.classify(model_by[rec["model"]],dataset.box(rec),rec,cfg["oracle_iterations"],cfg["oracle_max_nodes"])
            answers[rec["id"]]=ans
            stream.write(json.dumps({"id":rec["id"],"model":rec["model"],"oracle_seconds":perf_counter()-start,**ans})+"\n")
            stream.flush()
    print("Exact oracle complete:",len(answers),"queries; unknown:",sum(a["truth"]=="UNKNOWN" for a in answers.values()),flush=True)
    rows,preprocessing,diagnostics,decisions=[],[],[],[]
    with (out/"decisions.jsonl").open("w",encoding="utf-8") as trace:
        for name,n in scenarios:
            model=model_by[name]
            subset=[r for r in queries if r["model"]==name]
            fields={}
            for method in ("A","B","C"):
                start=perf_counter()
                fields[method]=Deformation(model,n,cfg["guard"],fast=method=="C")
                elapsed=perf_counter()-start
                preprocessing.append({"model":name,"grid":n,"method":method,"seconds":elapsed,
                                      "array_and_index_bytes":fields[method].storage_bytes})
            diagnostics.append(fields["B"].diagnostics())
            for budget in budgets:
                for j,rec in enumerate(subset):
                    box=dataset.box(rec)
                    order=("A","B","C") if j%2==0 else ("C","B","A")
                    for method in order:
                        engine=Engine(fields[method],dict(cfg,max_nodes=budget),method,index)
                        t=perf_counter()
                        result=engine.query(box)
                        elapsed=perf_counter()-t
                        valid=oracle.verify_result(model,box,result)
                        answer=answers[rec["id"]]["truth"]
                        incorrect=(valid is False or (answer!="UNKNOWN" and result["status"]!="UNRESOLVED" and answer!=result["status"]))
                        phase=sum(result["stats"][k] for k in ("localization_seconds","inverse_seconds","enclosure_seconds","geometry_seconds","subdivision_seconds"))
                        row={"id":rec["id"],"model":name,"grid":n,"method":method,"index":index,"budget":budget,
                             "group":rec["group"],"delta_over_h":rec["delta"]*n,"clearance_ratio_nominal":rec["clearance_ratio_nominal"],
                             "clearance_over_delta_actual":rec.get("clearance_over_delta_actual"),"tau":rec["tau"],
                             "decision_model":rec["decision_model"],"oracle_truth":answer,"status":result["status"],
                             "cause":result["cause"],"mechanism":mechanism(result,rec,answer,method),"seconds":elapsed,
                             "overhead_seconds":max(0.,elapsed-phase),"exact_witness_valid":valid,"incorrect":incorrect,**result["stats"]}
                        rows.append(row)
                        trace.write(json.dumps({"id":rec["id"],"model":name,"grid":n,"method":method,"budget":budget,"result":result})+"\n")
                        trace.flush()
            write_csv(out/"timings.csv",rows)
            write_csv(out/"preprocessing.csv",preprocessing)
            write_json(out/"mapping_diagnostics.json",diagnostics)
            print(f"{out.name}: {name} grid{n} complete ({len(rows)} rows)",flush=True)
    write_csv(out/"incorrect.csv",[r for r in rows if r["incorrect"]],list(rows[0]))
    write_csv(out/"unresolved.csv",[r for r in rows if r["status"]=="UNRESOLVED"],list(rows[0]))
    validation={"queries":len(queries),"rows":len(rows),"incorrect_rows":sum(r["incorrect"] for r in rows),
                "exact_witness_checks":sum(r["exact_witness_valid"] is True for r in rows),
                "oracle_unknown":sum(v["truth"]=="UNKNOWN" for v in answers.values()),
                "disjoint_rows_without_oracle_resolution":sum(r["status"]=="DISJOINT" and r["oracle_truth"]=="UNKNOWN" for r in rows),
                "parent_hashes_unchanged":json.loads((ROOT/"PARENT_PRESERVATION.json").read_text())==parent_inventory(),
                "production_formally_directed_rounded":False}
    write_json(out/"validation.json",validation)
    if validation["incorrect_rows"] or not validation["parent_hashes_unchanged"]:
        raise SystemExit("classification/preservation gate failed; saved cases require inspection")
    return rows


def coarse(output):
    cfg=configuration()
    models=cfg["models"]
    scenarios=[(m["name"],4) for m in models]+[(name,8) for name in ("nonlinear_mild","nonlinear_high","nonlinear_cond8")]
    freeze(output,{"phase":"coarse","scenarios":scenarios,"budgets":cfg["budgets"],"timing_repetitions":1})
    with (output/"unit_tests.log").open("w",encoding="utf-8") as stream:
        suite=unittest.defaultTestLoader.discover(str(ROOT/"tests"))
        result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
    if not result.wasSuccessful():
        raise SystemExit("preflight tests failed; inspect saved log")
    queries=sum((dataset.make(m,cfg["seed"]) for m in models),[])
    execute(output,models,queries,scenarios,cfg["budgets"])


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",type=Path,default=ROOT/"results/coarse")
    coarse(parser.parse_args().output.resolve())
