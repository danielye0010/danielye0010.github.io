"""Read-only parent checks, source/data consistency, and exact proof replay."""
import json
import os
import platform
import subprocess
import sys
from fractions import Fraction as F
from pathlib import Path
import numpy as np
from common import ROOT,PARENT,parent_inventory,sha,write_json,old_oracle as O
from qualify import read_csv
import oracle,dataset


def volume(q):
    v=F(1)
    for a,b in q:v*=b-a
    return v


def main():
    out=ROOT/'results/final_validation';out.mkdir(parents=True,exist_ok=True)
    assert json.loads((ROOT/'PARENT_PRESERVATION.json').read_text())==parent_inventory()
    snapshots={}
    for phase in ('coarse','refined','tolerance','controls'):
        folder=ROOT/'results'/phase
        freeze=json.loads((folder/'PRE_RUN_FREEZE.json').read_text())
        for name,digest in freeze['source_sha256'].items():
            assert sha(folder/'source'/name)==digest,(phase,name)
        assert sha(ROOT/'PARENT_PRESERVATION.json')==freeze['parent_preservation_sha256']
        snapshots[phase]=len(freeze['source_sha256'])
    models={};cases={};traces=[];rows=[]
    for phase in ('coarse','refined','tolerance'):
        folder=ROOT/'results'/phase
        payload=json.loads((folder/'queries.json').read_text())
        models.update({m['name']:m for m in payload['models']})
        cases.update({r['id']:r for r in payload['queries']})
        trace=[json.loads(v) for v in (folder/'decisions.jsonl').read_text().splitlines()]
        timing=read_csv(folder/'timings.csv')
        assert len(trace)==len(timing)
        for t,r in zip(trace,timing):
            assert all(str(t[k])==r[k] for k in ('id','model','grid','method','budget'))
            assert t['result']['status']==r['status']
            for k in ('nodes','splits','map_evals','jac_evals','candidates','max_depth'):
                assert str(t['result']['stats'][k])==r[k]
        traces+=trace;rows+=timing
    truth={r['id']:r for r in map(json.loads,(ROOT/'results/qualification/ground_truth.jsonl').read_text().splitlines())}
    supports={name:oracle.support(m) for name,m in models.items()}
    witnesses=0;support_proofs=0;interval_proofs=0
    for id,answer in truth.items():
        rec=cases[id];model=models[rec['model']];q=oracle.intervals(dataset.box(rec))
        if rec.get('support_point'):
            image,x=supports[rec['model']]
            assert F(rec['support_value'])==image[0]
            assert oracle.forward(model,tuple(F(v) for v in rec['support_point']))[0]==image[0]
        if answer['truth']=='DISJOINT':
            if 'support plane' in answer['proof']:
                assert q[0][0]>supports[rec['model']][0][0]
                support_proofs+=1
            else:
                cover=answer['cover'];rects=[]
                for leaf in cover:
                    rect=tuple(tuple(F(v) for v in p) for p in leaf['query'])
                    inv=tuple(tuple(F(v) for v in p) for p in leaf['preimage'])
                    assert all(a<=c<=d<=b for (a,b),(c,d) in zip(q,rect))
                    assert inv==oracle.inverse_box(model,rect,180)
                    assert O.solid_classify(inv)=='EMPTY'
                    rects.append(rect)
                assert sum(volume(v) for v in rects)==volume(q)
                for i,p in enumerate(rects):
                    for r in rects[i+1:]:
                        assert any(min(b,d)<=max(a,c) for (a,b),(c,d) in zip(p,r))
                interval_proofs+=1
        else:
            assert answer['truth']=='INTERSECTS'
            if answer.get('witness'):
                x=tuple(F(v) for v in answer['witness'])
                assert oracle.valid_witness(model,q,x,False)
            elif answer.get('preimage'):
                center=tuple(F(v) for v in answer['spatial_witness'])
                inv=oracle.inverse_box(model,tuple((v,v) for v in center),180)
                assert O.solid_classify(inv)=='FULL'
            elif answer['proof']=='exact singleton boundary contact':
                assert oracle.valid_witness(model,q,tuple(F(v) for v in rec['reference_seed']),False)
            else:
                raise AssertionError(('unsupported saved truth proof',id,answer))
    for trace in traces:
        rec=cases[trace['id']];result=trace['result']
        assert result['status']=='UNRESOLVED' or result['status']==truth[rec['id']]['truth']
        valid=oracle.verify_result(models[trace['model']],dataset.box(rec),result)
        assert valid is not False
        witnesses+=valid is True
    # Fresh subprocesses keep 00-A's oracle configuration intact and write
    # all stdout/stderr inside exp00b, with bytecode disabled.
    tests={}
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1')
    for name,cwd in [('00a',PARENT),('00b',ROOT)]:
        result=subprocess.run([sys.executable,'-B','-m','unittest','discover','-s','tests','-v'],
                              cwd=cwd,env=env,capture_output=True,text=True)
        (out/(name+'_unit_tests.log')).write_text(result.stdout+result.stderr,encoding='utf-8')
        assert result.returncode==0,(name,result.stderr)
        tests[name]=result.returncode
    # Regime-plot counts are rederived directly from raw rows and qualified
    # truths. This links the headline claims to the immutable dataset.
    for r in read_csv(ROOT/'results/analysis/figure_regime_map.csv'):
        selected=[v for v in rows if v['model']==r['model'] and v['grid']=='4' and v['budget']=='2047' and
            v['method']==r['method'] and v['decision_model']=='exact_closed_query' and
            v['group'] not in ('exact_contact','outer_numerical_floor','singleton_interior') and
            truth[v['id']]['truth']==r['truth']]
        assert len(selected)==int(r['n'])
        assert sum(v['status']==r['truth'] for v in selected)==int(r['resolved'])
    # Actual repeated batches must agree with the independently qualified
    # primary decisions for the same frozen boxes/budget. No answer caching.
    cfg=json.loads((ROOT/'config.json').read_text())
    mild=next(m for m in cfg['models'] if m['name']=='nonlinear_mild')
    regular=[r for r in dataset.make(mild,cfg['seed']) if r['group'] not in
             ('exact_contact','singleton_interior','outer_numerical_floor')]
    reference={(r['id'],r['method']):r for r in rows if r['model']=='nonlinear_mild' and
               r['grid']=='4' and r['budget']=='511' and r['decision_model']=='exact_closed_query'}
    batches=read_csv(ROOT/'results/controls/batches.csv')
    for r in batches:
        selected=[reference[(regular[j%len(regular)]['id'],r['method'])] for j in range(int(r['N']))]
        assert sum(int(v['nodes']) for v in selected)==int(r['nodes'])
        assert sum(v['status']=='UNRESOLVED' for v in selected)==int(r['unresolved'])
    control_check=json.loads((ROOT/'results/analysis/control_classification_validation.json').read_text())
    assert control_check['rows']==240 and not control_check['incorrect']
    import fitz
    figure_qa=[]
    for path in sorted((ROOT/'figures').glob('*.pdf')):
        doc=fitz.open(path)
        images=sum(len(page.get_images()) for page in doc)
        assert images==0 and len(doc)==1
        assert len(doc[0].get_text())>50
        figure_qa.append({'path':path.relative_to(ROOT).as_posix(),'pages':len(doc),'raster_images':images,'extractable_text':True})
    assert len(figure_qa)==3
    assert json.loads((ROOT/'PARENT_PRESERVATION.json').read_text())==parent_inventory()
    summary={'source_snapshot_files':snapshots,'primary_rows_rechecked':len(rows),'unique_query_truths':len(truth),
        'exact_production_intersection_checks':witnesses,'support_plane_disjoint_truths_replayed':support_proofs,
        'exact_interval_exclusion_covers_replayed':interval_proofs,'incorrect_classifications':0,
        'control_decisions_checked_against_exact_truth':control_check['rows'],
        'actual_batch_rows_consistent_with_qualified_primary':len(batches),
        'actual_batch_query_executions':sum(int(r['N']) for r in batches),
        'parent_00a_hashes_unchanged':True,'unit_test_exit_codes':tests,'figures':figure_qa,
        'runtime':{'python':sys.version,'numpy':np.__version__,'platform':platform.platform(),
            'processor':platform.processor(),'executable':sys.executable,'thread_limits':'1 (OpenBLAS/OMP/MKL benchmark environment)'},
        'floating_point_qualification':'mathematical bounds and exact finite-dataset checks; guarded binary64 production is not formally certified'}
    write_json(out/'validation.json',summary)
    write_json(ROOT/'ARTIFACT_MANIFEST.json',{p.relative_to(ROOT).as_posix():sha(p) for p in sorted(ROOT.rglob('*'))
        if p.is_file() and p.name!='ARTIFACT_MANIFEST.json' and not any(v in ('.mplconfig','__pycache__') for v in p.relative_to(ROOT).parts)})
    print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
