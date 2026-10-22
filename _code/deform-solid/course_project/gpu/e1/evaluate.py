"""Evaluate a dense lattice or an XYZ .npy batch using the native C++ DLL."""
from pathlib import Path
import argparse,json,time
import numpy as np
from native import Native,MODELS
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--library',type=Path);p.add_argument('--model',choices=MODELS,default='nonlinear_high')
p.add_argument('--n',type=int,default=1024);p.add_argument('--xyz',type=Path);p.add_argument('--radius',type=float,default=1/64)
p.add_argument('--output',required=True,type=Path)
a=p.parse_args()
if a.output.exists():raise FileExistsError(a.output)
native=Native(a.library);started=time.perf_counter()
if a.xyz:result=native.xyz(np.load(a.xyz),a.model,a.radius);native_s=None
else:
    buffers=native.node_buffers(a.n,a.model,a.radius);native_s=native.nodes(buffers,timed=True);result=buffers['arrays']
a.output.parent.mkdir(parents=True,exist_ok=True);np.savez_compressed(a.output,**result)
print(json.dumps(dict(output=str(a.output.resolve()),nodes=len(result['value']),native_compute_s=native_s,total_wall_including_export_s=time.perf_counter()-started,
    non_ok=int(np.count_nonzero(result['numeric_status']!=1)),interval_qualification=False)))
