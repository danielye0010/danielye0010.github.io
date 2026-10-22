"""Resolve initial oracle limitations and independently check every saved result."""
import csv
import json
from fractions import Fraction as F
from itertools import product
from common import ROOT,write_json,parent_inventory
from fields import affine_exact
import oracle,dataset


def read_csv(path):
    with path.open(newline="",encoding="utf-8") as f:
        return list(csv.DictReader(f))


def extended_witness(model,box):
    q=oracle.intervals(box)
    if model["amplitude"]==0:
        A,Ai,b=affine_exact(model)
        for corner in product(*q):
            x=tuple(sum(Ai[i][j]*(corner[j]-b[j]) for j in range(3)) for i in range(3))
            if oracle.valid_witness(model,q,x):
                return {"truth":"INTERSECTS","proof":"exact affine inverse corner witness",
                        "witness":[str(v) for v in x]}
    # Strictly inset points avoid a false floating equality at spatial corners.
    # They can certify INTERSECTS only; absence of a witness proves nothing.
    for weights in product((F(1,64),F(1,2),F(63,64)),repeat=3):
        target=tuple(a+t*(b-a) for (a,b),t in zip(q,weights))
        x=oracle.seed(model,target)
        if oracle.valid_witness(model,q,x):
            return {"truth":"INTERSECTS","proof":"extended independently checked exact witness",
                    "witness":[str(v) for v in x]}
    return None


def main():
    truths={}; models={};cases={};traces=[];rows=[];initial_unknown=[]
    for phase in ("coarse","refined","tolerance"):
        folder=ROOT/"results"/phase
        if not (folder/"validation.json").exists():
            continue
        payload=json.loads((folder/"queries.json").read_text())
        models.update({m["name"]:m for m in payload["models"]})
        cases.update({r["id"]:r for r in payload["queries"]})
        for line in (folder/"oracle.jsonl").read_text().splitlines():
            answer=json.loads(line)
            truths[answer["id"]]=answer
        rows.extend(dict(r,phase=phase) for r in read_csv(folder/"timings.csv"))
        traces.extend(json.loads(v) for v in (folder/"decisions.jsonl").read_text().splitlines())
    for id,answer in list(truths.items()):
        if answer["truth"]=="UNKNOWN":
            initial_unknown.append(answer)
            rec=cases[id]
            extra=extended_witness(models[rec["model"]],dataset.box(rec))
            if extra:
                truths[id]={"id":id,"model":rec["model"],"initial_oracle":"UNKNOWN",**extra}
    witness_checks=0
    bad=[]
    for trace in traces:
        rec=cases[trace["id"]];model=models[trace["model"]]
        result=trace["result"]
        valid=oracle.verify_result(model,dataset.box(rec),result)
        truth=truths[trace["id"]]["truth"]
        if valid is True:
            witness_checks+=1
            if truth=="UNKNOWN":
                truths[trace["id"]]={"id":trace["id"],"truth":"INTERSECTS",
                    "proof":"exact independent recomputation of production witness/root residual",
                    "initial_oracle":"UNKNOWN"}
                truth="INTERSECTS"
        if valid is False or (result["status"]!="UNRESOLVED" and truth!="UNKNOWN" and result["status"]!=truth):
            bad.append(trace)
    unresolved_truth=[id for id,a in truths.items() if a["truth"]=="UNKNOWN"]
    unverified_disjoint=sum(r["status"]=="DISJOINT" and truths[r["id"]]["truth"]=="UNKNOWN" for r in rows)
    out=ROOT/"results/qualification"
    out.mkdir(parents=True,exist_ok=True)
    with (out/"ground_truth.jsonl").open("w",encoding="utf-8") as f:
        for id in sorted(truths):
            f.write(json.dumps(truths[id])+"\n")
    write_json(out/"initial_oracle_unknown.json",initial_unknown)
    write_json(out/"incorrect.json",bad)
    summary={"rows_checked":len(rows),"queries":len(truths),"initial_oracle_unknown":len(initial_unknown),
             "final_ground_truth_unknown":len(unresolved_truth),"unknown_ids":unresolved_truth,
             "incorrect_classifications":len(bad),"exact_witnesses_rechecked":witness_checks,
             "unverified_disjoint_rows":unverified_disjoint,
             "parent_preserved":json.loads((ROOT/"PARENT_PRESERVATION.json").read_text())==parent_inventory(),
             "interpretation":"extended point searches only prove intersection; all disjoint truth uses interval/support exclusion"}
    write_json(out/"validation.json",summary)
    print(json.dumps(summary,indent=2))
    assert not bad and not unverified_disjoint and summary["parent_preserved"]


if __name__=="__main__":
    main()
