"""Saved-data analysis only; no query algorithms run here."""
import csv
import json
import os
from collections import defaultdict,Counter
from pathlib import Path
import numpy as np
from common import ROOT,write_json
from qualify import read_csv
from run import write_csv

REGULAR_EXCLUDE={'exact_contact','outer_numerical_floor','singleton_interior'}
PHASES=('localization','inverse','enclosure','geometry','subdivision')


def grouped(rows,keys):
    groups=defaultdict(list)
    for r in rows:
        groups[tuple(r[k] for k in keys)].append(r)
    return groups


def mean(rows,key):
    return float(np.mean([float(r[key]) for r in rows])) if rows else None


def summarize(rows,keys):
    output=[]
    for key,items in grouped(rows,keys).items():
        ans=dict(zip(keys,key));n=len(items)
        status=Counter(r['status'] for r in items)
        ans.update(n=n,resolved=sum(r['status']!='UNRESOLVED' for r in items),
                   resolved_fraction=sum(r['status']!='UNRESOLVED' for r in items)/n,
                   intersects=status['INTERSECTS'],disjoint=status['DISJOINT'],unresolved=status['UNRESOLVED'])
        for truth,label in [('INTERSECTS','I'),('DISJOINT','D')]:
            subset=[r for r in items if r['truth']==truth]
            ans[label+'_total']=len(subset)
            ans[label+'_resolved']=sum(r['status']==truth for r in subset)
            ans[label+'_resolution']=ans[label+'_resolved']/len(subset) if subset else None
        for metric in ('nodes','splits','map_evals','jac_evals','newton_iterations','candidates','max_depth',
                       'peak_pending','cell_tests','bvh_nodes','point_inverse_failures','mixed_enclosures',
                       'max_residual','seconds','max_enclosure_ratio'):
            ans['mean_'+metric]=mean(items,metric)
        ans['p95_nodes']=float(np.percentile([int(r['nodes']) for r in items],95))
        ans['maximum_depth']=max(int(r['max_depth']) for r in items)
        ans['point_failure_queries']=sum(int(r['point_inverse_failures'])>0 for r in items)
        for phase in PHASES:
            ans[phase+'_seconds']=sum(float(r[phase+'_seconds']) for r in items)
        ans['overhead_seconds']=sum(float(r['overhead_seconds']) for r in items)
        output.append(ans)
    return output


def main():
    out=ROOT/'results/analysis';out.mkdir(parents=True,exist_ok=True)
    truth={r['id']:r['truth'] for r in map(json.loads,(ROOT/'results/qualification/ground_truth.jsonl').read_text().splitlines())}
    rows=[];cases={}
    for phase in ('coarse','refined','tolerance'):
        folder=ROOT/'results'/phase
        data=json.loads((folder/'queries.json').read_text())
        cases.update({r['id']:r for r in data['queries']})
        for r in read_csv(folder/'timings.csv'):
            r.update(phase=phase,truth=truth[r['id']])
            # Group the intentionally preserved numerical-floor records by
            # construction, not by which terminal happened under a budget.
            if r['status']=='UNRESOLVED':
                if phase=='tolerance' and float(r['tau'])>0:
                    # Original family tags survive dilation but do NOT imply
                    # that the expanded query is still exact contact/near guard.
                    r['mechanism']=('inverse_region_subdivision' if r['method']!='A' else
                        ('forward_witness_search' if r['truth']=='INTERSECTS' else 'forward_exclusion_search'))
                elif r['group']=='outer_numerical_floor':
                    r['mechanism']='near_guard_clearance'
            rows.append(r)
    keys=('phase','model','grid','method','budget')
    for scope,predicate in [('all',lambda r:True),('regular',lambda r:r['group'] not in REGULAR_EXCLUDE),
                            ('contact',lambda r:r['group']=='exact_contact'),
                            ('near_guard',lambda r:r['group']=='outer_numerical_floor'),
                            ('singleton',lambda r:r['group']=='singleton_interior')]:
        chosen=[r for r in rows if predicate(r)]
        if chosen:write_csv(out/(scope+'_summary.csv'),summarize(chosen,keys))
    write_csv(out/'group_summary.csv',summarize(rows,keys+('group',)))
    mechanisms=[]
    for key,items in grouped([r for r in rows if r['status']=='UNRESOLVED'],keys+('mechanism','cause')).items():
        mechanisms.append(dict(zip(keys+('mechanism','cause'),key),n=len(items),
            total_nodes=sum(int(r['nodes']) for r in items),mean_nodes=mean(items,'nodes'),
            mean_map_evals=mean(items,'map_evals'),mean_jac_evals=mean(items,'jac_evals')))
    write_csv(out/'unresolved_mechanisms.csv',mechanisms)
    clear=[dict(r,clearance_ratio=cases[r['id']]['clearance_ratio_nominal']) for r in rows
           if r['phase']=='coarse' and r['grid']=='4' and r['group'] in ('outer_clearance','outer_numerical_floor')]
    write_csv(out/'clearance_summary.csv',summarize(clear,('model','method','budget','clearance_ratio')))
    tau=[r for r in rows if r['phase']=='tolerance']
    write_csv(out/'tolerance_summary.csv',summarize(tau,('model','method','tau')))
    changes=[]
    for rec in cases.values():
        if rec.get('original_id'):
            changes.append({'id':rec['id'],'model':rec['model'],'tau':rec['tau'],
                'original_truth':truth[rec['original_id']],'dilated_truth':truth[rec['id']],
                'changed':truth[rec['original_id']]!=truth[rec['id']],
                'clearance_over_original_delta':rec.get('clearance_over_delta_actual')})
    write_csv(out/'tolerance_truth_changes.csv',changes)
    # Correct the name of the diagnostic in early snapshots: original 00-A
    # q first unions derivative entries over cells, then takes row sums.
    # This does not change ANY executed algorithm or raw result.
    from fields import Deformation
    diagnostics=[];seen=set()
    for phase in ('coarse','refined'):
        for d in json.loads((ROOT/'results'/phase/'mapping_diagnostics.json').read_text()):
            key=(d['model']['name'],d['grid'])
            if key not in seen:
                diagnostics.append(dict(phase=phase,**Deformation(d['model'],d['grid']).diagnostics()))
                seen.add(key)
    write_json(out/'mapping_diagnostics_corrected.json',diagnostics)
    paired=grouped(rows,('phase','id','grid','budget'))
    differences=[]
    for key,items in paired.items():
        a={r['method']:r for r in items};b,c=a['B'],a['C']
        diff=[k for k in ('status','nodes','map_evals','jac_evals','newton_iterations','cause') if b[k]!=c[k]]
        if diff:differences.append({'key':key,'differences':diff})
    write_json(out/'implementation_control_differences.json',differences)
    controls=read_csv(ROOT/'results/controls/timings.csv')
    bad=[r for r in controls if r['status']!='UNRESOLVED' and r['status']!=truth[r['id']]]
    write_json(out/'control_classification_validation.json',{'rows':len(controls),'incorrect':bad})
    assert not bad
    control_summary=[]
    for key,items in grouped(controls,('grid','method','index','clip')).items():
        control_summary.append(dict(zip(('grid','method','index','clip'),key),
            mean_seconds=mean(items,'seconds'),median_seconds=float(np.median([float(r['seconds']) for r in items])),
            mean_nodes=mean(items,'nodes'),unresolved=sum(r['status']=='UNRESOLVED' for r in items),n=len(items)))
    write_csv(out/'control_summary.csv',control_summary)
    batches=read_csv(ROOT/'results/controls/batches.csv')
    write_csv(out/'batch_summary.csv',[dict(zip(('N','method'),key),
        median_total_seconds=float(np.median([float(r['total_seconds']) for r in items])),
        median_query_seconds=float(np.median([float(r['query_seconds']) for r in items])),
        median_preprocess_seconds=float(np.median([float(r['preprocess_seconds']) for r in items])),
        min_total_seconds=min(float(r['total_seconds']) for r in items),
        max_total_seconds=max(float(r['total_seconds']) for r in items),unresolved=int(items[0]['unresolved']))
        for key,items in grouped(batches,('N','method')).items()])
    figures(rows,cases,out)
    write_json(out/'summary.json',{'rows':len(rows),'unique_queries':len(cases),'B_C_differing_pairs':len(differences),
        'control_rows':len(controls),'budget_definition':'visited subdivision regions, not equal operation cost',
        'primary_timing_repetitions':1,'secondary_control_repetitions':3,
        'diagnostic_correction':'early coarse/refined legacy_q label stored tighter per-cell quantity; corrected values here use 00-A entrywise global union. No decision used this diagnostic.'})
    print(json.dumps(json.loads((out/'summary.json').read_text()),indent=2))


def figures(rows,cases,out):
    os.environ['MPLCONFIGDIR']=str(ROOT/'.mplconfig')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,'svg.fonttype':'none','pdf.fonttype':42,
        'axes.spines.top':False,'axes.spines.right':False,'axes.linewidth':.6,'savefig.dpi':180})
    folder=ROOT/'figures';folder.mkdir(exist_ok=True)
    def save(fig,name):
        for suffix in ('svg','pdf','png'):fig.savefig(folder/(name+'.'+suffix),bbox_inches='tight')
        plt.close(fig)
    labels={'A':'A forward','B':'B Newton','C':'C scalar control'}
    colors={'A':'#333333','B':'#0072B2','C':'#D55E00'}
    models=list(dict.fromkeys(r['model'] for r in rows if r['phase']=='coarse' and r['grid']=='4'))
    models+=list(dict.fromkeys(r['model'] for r in rows if r['phase']=='refined'))
    display={'identity':'Identity','rotation53':'Rigid 53.1 deg','rotation90':'Rigid 90 deg',
        'affine_cond8':'Affine: stretch 1/8','nonlinear_mild':'Q1: amplitude 1','nonlinear_high':'Q1: amplitude 2',
        'nonlinear_rotation53':'Q1 + rigid 53.1 deg','nonlinear_cond8':'Q1 + stretch 1/8',
        'nonlinear_qnear_33_16':'Q1: q = 495/512','nonlinear_qnear_67_32':'Q1: q = 1005/1024',
        'nonlinear_cond32':'Q1 + stretch 1/32','affine_cond32':'Affine: stretch 1/32'}
    fig,axes=plt.subplots(1,2,figsize=(7.2,5),sharey=True,layout='constrained')
    plotdata=[]
    for ax,truth,title in zip(axes,('INTERSECTS','DISJOINT'),('Intersecting truth','Disjoint truth')):
        values=np.zeros((len(models),3))
        for i,name in enumerate(models):
            for j,method in enumerate(('A','B','C')):
                chosen=[r for r in rows if r['model']==name and r['grid']=='4' and r['method']==method and
                    r['budget']=='2047' and r['phase']!='tolerance' and r['group'] not in REGULAR_EXCLUDE and r['truth']==truth]
                k=sum(r['status']==truth for r in chosen);n=len(chosen);values[i,j]=k/n
                plotdata.append({'model':name,'method':method,'truth':truth,'resolved':k,'n':n})
                ax.text(j,i,f'{k}/{n}',ha='center',va='center',fontsize=8,color='white' if k/n<.5 else 'black')
        im=ax.pcolormesh(np.arange(4)-.5,np.arange(len(models)+1)-.5,values,
                        cmap='Greys_r',vmin=0,vmax=1,shading='flat')
        ax.set_ylim(len(models)-.5,-.5)
        ax.set_xticks(range(3),['A','B','C']);ax.set_title(title)
        ax.set_yticks(range(len(models)),[display.get(m,m) for m in models]);ax.tick_params(length=0)
    colorbar=fig.colorbar(im,ax=axes,label='Resolved fraction',shrink=.65)
    colorbar.solids.set_rasterized(False)
    fig.suptitle('Regular queries, 2,047 visited-region budget; exact class denominators')
    save(fig,'regime_map');write_csv(out/'figure_regime_map.csv',plotdata)
    fig,axes=plt.subplots(1,2,figsize=(7.5,3.0),layout='constrained')
    ratios=(-1/32,-1/2**24,1/2**24,1/1024,1/32)
    plotdata=[]
    for method in ('A','B','C'):
        ys=[]
        for ratio in ratios:
            subset=[r for r in rows if r['phase']=='coarse' and r['grid']=='4' and r['budget']=='2047' and
                r['method']==method and r['group'] in ('outer_clearance','outer_numerical_floor') and
                cases[r['id']]['clearance_ratio_nominal']==ratio]
            k=sum(r['status']!='UNRESOLVED' for r in subset);n=len(subset);ys.append(100*k/n)
            plotdata.append({'panel':'clearance','method':method,'coordinate':ratio,'resolved':k,'n':n})
        axes[0].plot(range(5),ys,marker={'A':'o','B':'s','C':'^'}[method],color=colors[method],
                     linestyle='-' if method!='C' else ':',label=labels[method])
    axes[0].set_xticks(range(5),['-1/32','-2^-24','+2^-24','+1/1024','+1/32'],rotation=25)
    axes[0].set_xlabel('Signed support clearance / query size')
    axes[0].set_title('All eight coarse fields; floors retained')
    taus=sorted({float(r['tau']) for r in rows if r['phase']=='tolerance'})
    for method in ('A','B','C'):
        ys=[]
        for tau in taus:
            subset=[r for r in rows if r['phase']=='tolerance' and r['method']==method and float(r['tau'])==tau]
            k=sum(r['status']!='UNRESOLVED' for r in subset);n=len(subset);ys.append(100*k/n)
            plotdata.append({'panel':'tolerance','method':method,'coordinate':tau,'resolved':k,'n':n})
        axes[1].plot(range(len(taus)),ys,marker={'A':'o','B':'s','C':'^'}[method],color=colors[method],
                     linestyle='-' if method!='C' else ':',label=labels[method])
    axes[1].set_xticks(range(len(taus)),['0','2^-28','2^-20','2^-14'])
    axes[1].set_xlabel('Spatial query dilation tau (different task)')
    axes[1].set_title('Three Q1 fields; 12 cases per tau')
    for ax in axes:ax.set_ylim(-3,103);ax.set_ylabel('Resolved (%)');ax.grid(axis='y',alpha=.2)
    handles,legends=axes[1].get_legend_handles_labels()
    fig.legend(handles,legends,fontsize=8,loc='outside lower center',ncol=3)
    save(fig,'clearance_tolerance');write_csv(out/'figure_clearance_tolerance.csv',plotdata)
    # Unresolved work by recorded mechanism, not an inferred failure label.
    fig,axes=plt.subplots(1,2,figsize=(7.5,3.2),layout='constrained')
    order=('inverse_region_subdivision','forward_witness_search','forward_exclusion_search','exact_contact',
           'near_guard_clearance','numerical_or_spatial_floor','singleton_witness_availability')
    names=('Inverse enclosure','Forward witness','Forward exclusion','Exact contact','Near-guard clearance','Width floor','Singleton witness')
    selected=[r for r in rows if r['phase']=='coarse' and r['grid']=='4' and r['budget']=='2047' and r['status']=='UNRESOLVED']
    plotdata=[]
    for j,method in enumerate(('A','B','C')):
        vals=[]
        for mechanism in order:
            subset=[r for r in selected if r['method']==method and r['mechanism']==mechanism]
            work=sum(int(r['nodes']) for r in subset);vals.append(work/1000)
            plotdata.append({'method':method,'mechanism':mechanism,'queries':len(subset),'total_nodes':work})
        axes[0].barh(np.arange(len(order))+(j-1)*.23,vals,height=.23,color=colors[method],label=method)
    axes[0].set_yticks(range(len(order)),names);axes[0].invert_yaxis();axes[0].set_xlabel('Visited regions (thousands)')
    axes[0].set_title('Unresolved work across coarse n=4 cases')
    axes[0].legend(ncol=3,fontsize=8,loc='upper center',bbox_to_anchor=(.5,-.22))
    # Aggregate exclusive timers for regular mild vs high field; same region
    # budget gives different operation counts, as shown in the tables.
    phases=PHASES+('overhead',);phasecolors=('#bdbdbd','#0072B2','#88ccee','#e69f00','#999933','#f0f0f0')
    selected2=[r for r in rows if r['phase']=='coarse' and r['grid']=='4' and r['budget']=='2047' and
        r['group'] not in REGULAR_EXCLUDE and r['model'] in ('nonlinear_mild','nonlinear_high')]
    left=np.zeros(3)
    for phase,color in zip(phases,phasecolors):
        values=[sum(float(r[phase+'_seconds']) for r in selected2 if r['method']==m) for m in ('A','B','C')]
        axes[1].barh(range(3),values,left=left,color=color,label=phase,edgecolor='white',linewidth=.3);left+=values
    axes[1].set_yticks(range(3),['A','B','C']);axes[1].invert_yaxis();axes[1].set_xlabel('Aggregate instrumented time (s)')
    axes[1].set_title('Regular mild + high Q1 workloads')
    axes[1].legend(fontsize=7,ncol=3,loc='upper center',bbox_to_anchor=(.5,-.22))
    save(fig,'work_mechanisms');write_csv(out/'figure_work_mechanisms.csv',plotdata)


if __name__=='__main__':main()
