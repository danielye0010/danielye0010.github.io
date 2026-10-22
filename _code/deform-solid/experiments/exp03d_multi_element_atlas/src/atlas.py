from pathlib import Path
import sys,json,csv,hashlib,itertools,time
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1];R=ROOT/'results';PRE=ROOT.parent/'exp03c_interface_regularization';A=ROOT.parent/'exp03a_modal_local_inverse';B=ROOT.parent/'exp03b_two_mode_qualification'
sys.path.insert(0,str(PRE/'src'))
from interface import DD,stack,shift,field_coefficients,norm,forward,Fdd,jacobian,tensors,full_jet,rays,inverse,coefficients,sha
from numerics import solve,h,tr
from face import face_candidates
FRACTIONS=np.array([.25,.50,.75,.95]);TAUS=[1e-4,1e-3,1e-2,.05]
def write(name,rows,fields=None):
 with (R/name).open('x',newline='') as fp:w=csv.DictWriter(fp,fieldnames=fields or list(rows[0]));w.writeheader();w.writerows(rows)
def load():return np.load(A/'inputs/field.npz'),json.loads((ROOT/'FROZEN_PROTOCOL.json').read_text())
def enc(x):return dict(hi=x.h.tolist(),lo=x.l.tolist())
def dec(x):return DD(x['hi'],x['lo'])
def freeze():
 p=json.loads((PRE/'FROZEN_PROTOCOL.json').read_text());v=json.loads((PRE/'results/final_verification.json').read_text());assert v['all_checks_pass'] and v['status']=='EXP3C-INTERFACE-QUALIFIED'
 for name,hsh in p['source_hashes'].items():assert sha(Path(name))==hsh
 files=[A/'inputs/field.npz',A/'src/numerics.py',A/'src/prepare.py',A/'EXP03A_REPORT.md',A/'DERIVATION_MODAL_LOCAL_INVERSE.md',B/'EXP03B_QUALIFICATION_REPORT.md',PRE/'EXP03C_QUALIFICATION_REPORT.md',PRE/'DERIVATION_INTERFACE_REGULARITY.md',PRE/'FROZEN_PROTOCOL.json',PRE/'results/topology.npz',PRE/'src/interface.py',PRE/'results/interface_crossings.csv']
 cfg=dict(fields=p['fields'],element_indices=p['element_indices'],directions=p['directions'],fractions=FRACTIONS.tolist(),tolerances=TAUS,crossings=3,evaluated_segments=3,minimum_coverage=200,edge_gate=.95,grazing_gate=.15,continuity_gate=1e-11,residual_gate=1e-24,stitch_gate=1e-12,jet_gate=1e-10,hp_error_gate=1e-7,hp_value_absolute_over_h_gate=1e-24,hp_digits=80,triangle_tolerance_over_h=1e-24,progress_floor_over_h=1e-20,tie_gap_over_h=1e-12,hp_selection='first, len//2, last retained path per field in original anchor/direction traversal; all segments, fractions .25 and .95',stitching='only approximate predecessor chart plus accumulated offset minus approximate entering chart; terminal third-interface correction checked but no e3 interior queries',arithmetic='DD full-index same A/B/C formula; checked against original binary64 full_jet and DD ray recurrence',source_hashes={str(x):sha(x) for x in files},request_sha256=sha(ROOT/'REQUEST.md'),status='FROZEN-BEFORE-TRACING-AND-ERRORS')
 with (ROOT/'FROZEN_PROTOCOL.json').open('x') as fp:json.dump(cfg,fp,indent=2)
 print('FROZEN 4 x 64 x 48 paths',flush=True)
def cached_coefficients(z,field,components):
 p=R/f'coefficients_{field}.npz'
 if p.exists():
  x=np.load(p);return [[DD(a,b) for a,b in zip(aa,bb)] for aa,bb in zip(x['hi'],x['lo'])]
 cs=field_coefficients(z,components);np.savez(p,hi=np.array([[v.h for v in c] for c in cs]),lo=np.array([[v.l for v in c] for c in cs]));return cs

def trace_paths(field):
 z,f=load();cs=cached_coefficients(z,field,f['fields'][field]);top=np.load(PRE/'results/topology.npz');nf=top['neighbor'];opp=top['neighbor_face'];rows=[];events=[];paths=[];start=time.monotonic();bounds={};fieldindex=list(f['fields']).index(field)
 def bound(e):
  if e not in bounds:bounds[e]=float(np.linalg.svd(jacobian(cs[e],DD(z['local']*z['half'][e]))-np.eye(3),compute_uv=False)[:,0].max())
  return bounds[e]
 for ai,e0 in enumerate(f['element_indices']):
  for di,dd in enumerate(f['directions']):
   d=np.array(dd);pid=fieldindex*3072+ai*48+di;e=e0;X0=DD(z['centers'][e0])+cs[e0][0];sprev=DD(0.);crossings=[];elements=[e];classification='PRIMARY';he=min(z['half'][e0]);entry=-1
   for j in range(3):
    if bound(e)>=1:raise RuntimeError('MULTI-ELEMENT-TRUTH-FAIL: chart injectivity bound')
    offset=X0-DD(z['centers'][e])-cs[e][0];cand=face_candidates(cs[e],z['half'][e],d,offset);cand=[c for c in cand if float((c[3]-sprev).val())>f['progress_floor_over_h']*he]
    if not cand:classification='NO-VALID-FORWARD-CROSSING';break
    _,face,y,s,res=cand[0];en=int(nf[e,face]);xc=DD(z['centers'][e])+y;Xc=X0+DD(d)*s;nat=y.val()/z['half'][e];free=[k for k in range(3) if k!=face//2];gap=float((cand[1][3]-s).val())/he if len(cand)>1 else np.inf;status='VALID';cm=shift(cs[e],y);detm=float(np.linalg.det(Fdd(cm).val()));gp=gm=cont=detp=np.nan
    if en<0:status='EXTERNAL-BOUNDARY'
    elif max(abs(nat[free]))>f['edge_gate']:status='EDGE_OR_VERTEX_PROXIMITY'
    elif gap<=f['tie_gap_over_h']:status='NONUNIQUE-FIRST-CROSSING'
    else:
     cp=shift(cs[en],xc-DD(z['centers'][en]));rm=solve(Fdd(cm),DD(d)).val();rp=solve(Fdd(cp),DD(d)).val();gm=abs(rm[face//2])/norm(rm);gp=abs(rp[face//2])/norm(rp);detp=float(np.linalg.det(Fdd(cp).val()));cont=max(float(norm((cm[0]-cp[0]).val())/he),float(norm((xc+cm[0]-Xc).val())/he),float(norm((xc+cp[0]-Xc).val())/he))
     if cont>f['continuity_gate'] or min(detm,detp)<=0:raise RuntimeError('MULTI-ELEMENT-TRUTH-FAIL: crossing continuity/Jacobian')
     if min(gm,gp)<f['grazing_gate']:status='GRAZING_CROSSING'
    event=dict(path_id=pid,field=field,crossing=j+1,source_element=e+1,neighbor_element=en+1,face=face,neighbor_face=int(opp[e,face]),s=float(s.val()),xi=nat[0],eta=nat[1],zeta=nat[2],face_residual_over_h=res,continuity_over_h=cont,det_minus=detm,det_plus=detp,grazing_minus=gm,grazing_plus=gp,next_candidate_gap_over_h=gap,source_gradient_bound=bound(e),classification=status);events.append(event)
    if status!='VALID':classification=status;break
    crossings.append(dict(source=e,neighbor=en,face=face,s=enc(s),x=enc(xc),X=enc(Xc),y=enc(y)));elements.append(en);e=en;sprev=s;entry=int(opp[elements[-2],face])
   rows.append(dict(path_id=pid,field=field,anchor=ai+1,direction=di+1,source_element=e0+1,valid_crossings=len(crossings),elements=json.dumps([el+1 for el in elements]),classification=classification))
   if classification=='PRIMARY':paths.append(dict(path_id=pid,field=field,anchor=ai+1,direction=di+1,elements=elements,X0=enc(X0),crossings=crossings))
  if ai%8==0:print(field,'anchors',ai+1,'retained',len(paths),'seconds',round(time.monotonic()-start,1),flush=True)
 write(f'topology_{field}.csv',rows);write(f'crossings_{field}.csv',events);(R/f'paths_{field}.json').write_text(json.dumps(paths));ids=[p['path_id'] for p in paths];(R/f'hp_ids_{field}.json').write_text(json.dumps([ids[0],ids[len(ids)//2],ids[-1]] if ids else []));print(field,'TRACE COMPLETE',len(paths),flush=True)

def full_jet_dd(c):
 F=Fdd(c);av=[solve(F,DD(np.eye(3)[:,j])) for j in range(3)];bb={};cc={}
 for j,k in itertools.product(range(3),repeat=2):bb[j,k]=solve(F,-h(c,av[j],av[k]))
 for j,k,l in itertools.product(range(3),repeat=3):cc[j,k,l]=solve(F,-tr(c,av[j],av[k],av[l])-h(c,bb[j,k],av[l])-h(c,bb[j,l],av[k])-h(c,bb[k,l],av[j]))
 def pack(vs,degree):
  hi=np.zeros((3,)*(degree+1));lo=hi.copy()
  for index,v in vs.items():hi[(slice(None),)+index]=v.h;lo[(slice(None),)+index]=v.l
  return DD(hi,lo)
 return pack({(j,):v for j,v in enumerate(av)},1),pack(bb,2),pack(cc,3)
def contract(t,delta,degree):
 v=DD(np.zeros(delta.h.shape))
 for index in itertools.product(range(3),repeat=degree):
  fac=DD(np.ones(delta.h.shape[:-1]))
  for j in index:fac=fac*delta[...,j]
  v=v+t[(slice(None),)+index]*fac[...,None]
 return v

def chart_values(chart,X):
 delta=X-chart['X'];out=[];total=DD(np.zeros(delta.h.shape))
 for degree,den in ((1,1),(2,2),(3,6)):
  total=total+contract(chart['jets'][degree-1],delta,degree)/den;out.append(DD(chart['center'])+total)
 return out

def stitch(previous_values,next_values,previous_correction):
 # Deliberately accepts no reference crossing point and no inverse truth.
 return [left+old-right for left,right,old in zip(previous_values,next_values,previous_correction)]

def evaluate_paths(field):
 z,f=load();cs=cached_coefficients(z,field,f['fields'][field]);paths=json.loads((R/f'paths_{field}.json').read_text());hpids=set(json.loads((R/f'hp_ids_{field}.json').read_text()));needed=sorted(set(e for p in paths for e in p['elements']));charts={};chartrows=[];begin=time.monotonic()
 for e in needed:
  c=cs[e];F=Fdd(c).val();_,H,T=tensors(c);ordinary=full_jet(F,H,T);jets=full_jet_dd(c);diff=max(norm((dd.val()-ff).ravel())/max(norm(ff.ravel()),1e-30) for dd,ff in zip(jets,ordinary));ray=rays(c,np.array(f['directions']));r2=contract(jets[1],DD(f['directions']),2)/2;r3=contract(jets[2],DD(f['directions']),3)/6;rgap=max(np.max(norm((r2-ray[1]).val())/np.maximum(norm(ray[1].val()),1e-20)),np.max(norm((r3-ray[2]).val())/np.maximum(norm(ray[2].val()),1e-20)));bound=float(np.linalg.svd(jacobian(c,DD(z['local']*z['half'][e]))-np.eye(3),compute_uv=False)[:,0].max());assert max(diff,rgap)<=f['jet_gate'],'ELEMENT-CHART-FAIL';assert np.linalg.det(F)>0 and bound<1,'MULTI-ELEMENT-TRUTH-FAIL'
  charts[e]=dict(center=z['centers'][e],X=DD(z['centers'][e])+c[0],jets=jets);chartrows.append(dict(field=field,element=e+1,center=json.dumps(z['centers'][e].tolist()),current_center=json.dumps(charts[e]['X'].val().tolist()),F=json.dumps(F.tolist()),H=json.dumps(H.tolist()),T=json.dumps(T.tolist()),A=json.dumps(jets[0].val().tolist()),B=json.dumps(jets[1].val().tolist()),C=json.dumps(jets[2].val().tolist()),minimum_sigma=np.linalg.svd(F,compute_uv=False)[-1],det=np.linalg.det(F),full_element_gradient_bound=bound,full_index_relative_gap=diff,ray_relative_gap=rgap))
 write(f'charts_{field}.csv',chartrows);np.savez(R/f'charts_dd_{field}.npz',elements=needed,Ahi=np.array([charts[e]['jets'][0].h for e in needed]),Alo=np.array([charts[e]['jets'][0].l for e in needed]),Bhi=np.array([charts[e]['jets'][1].h for e in needed]),Blo=np.array([charts[e]['jets'][1].l for e in needed]),Chi=np.array([charts[e]['jets'][2].h for e in needed]),Clo=np.array([charts[e]['jets'][2].l for e in needed]));print(field,'CHARTS',len(needed),'seconds',round(time.monotonic()-begin,1),flush=True)
 qrows=[];erows=[];mrows=[];crows=[];saved=[]
 for pi,path in enumerate(paths):
  pid=path['path_id'];els=path['elements'];d=DD(f['directions'][path['direction']-1]);X0=dec(path['X0']);he=min(z['half'][els[0]]);corrections=[[DD(np.zeros(3)) for _ in range(3)]];raw=dict(path_id=pid,corrections=[],queries=[])
  for j,xcross in enumerate(path['crossings']):
   Xc=dec(xcross['X']);left=chart_values(charts[els[j]],Xc);right=chart_values(charts[els[j+1]],Xc);new=stitch(left,right,corrections[-1]);xc=dec(xcross['x'])
   for k in range(3):
    mismatch=float(norm((left[k]-right[k]).val()));em=float(norm((left[k]-xc).val()));ep=float(norm((right[k]-xc).val()));identity=float(norm((left[k]+corrections[-1][k]-right[k]-new[k]).val())/he);triangle=max(0.,mismatch-em-ep)/he;assert identity<=f['stitch_gate'],'ATLAS-STITCHING-FAIL';assert triangle<=f['triangle_tolerance_over_h'],'MULTI-ELEMENT-TRUTH-FAIL: triangle'
    mrows.append(dict(path_id=pid,field=field,crossing=j+1,order=k+1,raw_mismatch=mismatch,raw_mismatch_over_h=mismatch/he,left_error_over_h=em/he,right_error_over_h=ep/he,triangle_excess_over_h=triangle,stitched_continuity_over_h=identity,terminal_only=j==2));crows.append(dict(path_id=pid,field=field,crossing=j+1,order=k+1,correction=json.dumps(new[k].val().tolist()),correction_norm=norm(new[k].val()),correction_over_h=norm(new[k].val())/he,terminal_only=j==2))
   corrections.append(new);raw['corrections'].append([enc(v) for v in new])
  for seg in range(3):
   e=els[seg];sa=DD(0.) if seg==0 else dec(path['crossings'][seg-1]['s']);sb=dec(path['crossings'][seg]['s']);ss=sa+(sb-sa)*DD(FRACTIONS);X=X0+d*ss[:,None];target=X-charts[e]['X'];initial=solve(Fdd(cs[e]),target);sol,res,det,it=inverse(cs[e],target,initial,he);natural=sol.val()/z['half'][e];truth=DD(z['centers'][e])+sol;assert max(res)<=f['residual_gate'] and min(det)>0 and np.max(abs(natural))<1,'MULTI-ELEMENT-TRUTH-FAIL';fixed=chart_values(charts[els[0]],X);rawv=chart_values(charts[e],X);stitched=[v+corrections[seg][k] for k,v in enumerate(rawv)];pert=np.full(4,np.nan)
   if pid in hpids:
    sol2,r2,d2,_=inverse(cs[e],target,initial+DD(he*np.array([.001,-.002,.0015])),he);pert=norm((sol-sol2).val())/he;assert max(pert)<=1e-24 and max(r2)<=1e-24 and min(d2)>0,'MULTI-ELEMENT-TRUTH-FAIL'
   errors={name:np.stack([norm((truth-v).val())/he for v in values],axis=-1) for name,values in [('fixed',fixed),('raw',rawv),('C0',stitched)]}
   for ri,frac in enumerate(FRACTIONS):
    qrows.append(dict(path_id=pid,field=field,segment=seg,fraction=frac,element=e+1,s=float(ss[ri].val()),reference_point=json.dumps(truth[ri].val().tolist()),forward_residual_over_h=res[ri],minimum_path_det=det[ri],max_abs_natural=max(abs(natural[ri])),perturbed_gap_over_h=pert[ri],status='VALID'))
    for k in range(3):erows.append(dict(path_id=pid,field=field,segment=seg,fraction=frac,order=k+1,fixed=errors['fixed'][ri,k],raw=errors['raw'][ri,k],C0=errors['C0'][ri,k]))
    if pid in hpids:raw['queries'].append(dict(segment=seg,fraction=frac,s=enc(ss[ri]),X=enc(X[ri]),truth=enc(truth[ri]),fixed=[enc(v[ri]) for v in fixed],raw=[enc(v[ri]) for v in rawv],C0=[enc(v[ri]) for v in stitched],errors={name:val[ri].tolist() for name,val in errors.items()}))
  if pid in hpids:saved.append(raw)
  if pi%200==0:print(field,'EVALUATED',pi+1,'seconds',round(time.monotonic()-begin,1),flush=True)
 write(f'queries_{field}.csv',qrows);write(f'errors_{field}.csv',erows);write(f'mismatch_{field}.csv',mrows);write(f'corrections_{field}.csv',crows);(R/f'hp_batch_{field}.json').write_text(json.dumps(saved));print(field,'EVALUATION COMPLETE',len(qrows),'queries',flush=True)
if __name__=='__main__':
 if sys.argv[1]=='freeze':freeze()
 elif sys.argv[1]=='trace':trace_paths(sys.argv[2])
 elif sys.argv[1]=='evaluate':evaluate_paths(sys.argv[2])
