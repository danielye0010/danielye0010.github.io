"""Thin one-call batch adapter; all per-query math is in e1_native.dll."""
from pathlib import Path
import ctypes as C
import numpy as np
ROOT=Path(__file__).resolve().parent
MODELS={'identity':0,'affine':1,'nonlinear_mild':2,'nonlinear_high':3}
D=C.POINTER(C.c_double); U8=C.POINTER(C.c_uint8); U32=C.POINTER(C.c_uint32); U64=C.POINTER(C.c_uint64)


class Model(C.Structure):
    _fields_=[('abi_version',C.c_uint32),('model_id',C.c_uint32),('hole_count',C.c_uint32),('reserved',C.c_uint32),
        ('lo',C.c_double*3),('hi',C.c_double*3),('holes',D)]
class Options(C.Structure):
    _fields_=[('abi_version',C.c_uint32),('max_iterations',C.c_uint32),('line_search_steps',C.c_uint32),('reserved',C.c_uint32),('field_tolerance',C.c_double)]
class Plane(C.Structure): _fields_=[('origin',C.c_double*3),('u',C.c_double*3),('v',C.c_double*3)]
class Window(C.Structure): _fields_=[('lo',C.c_double*2),('hi',C.c_double*2)]
DOUBLES=['value','field_lower','field_upper','source_x','source_y','source_z','inverse_error_inf',
    'residual_x','residual_y','residual_z','residual_inf','guarded_inverse_error','guarded_field_error']
BYTES=['qualification','numeric_status','failure_reason']
COUNTS=['iterations','fixedpoint_fallbacks']
class Output(C.Structure):
    _fields_=[(name,D) for name in DOUBLES]+[(name,U8) for name in BYTES]+[('guarded_sign',C.POINTER(C.c_int8))]+[(name,U32) for name in COUNTS]


def allocate(count):
    arrays={name:np.empty(count,np.float64) for name in DOUBLES}
    arrays.update({name:np.empty(count,np.uint8) for name in BYTES})
    arrays['guarded_sign']=np.empty(count,np.int8)
    arrays.update({name:np.empty(count,np.uint32) for name in COUNTS})
    out=Output(**{name:arr.ctypes.data_as(dict(Output._fields_)[name]) for name,arr in arrays.items()})
    return arrays,out


class Native:
    def __init__(self,path=None):
        self.path=Path(path or ROOT/'build_native/e1_native.dll').resolve()
        self.dll=C.CDLL(str(self.path))
        self.dll.e1_abi_version.restype=C.c_uint32
        if self.dll.e1_abi_version()!=1:raise ValueError('ABI version mismatch')
        self.dll.e1_default_model.argtypes=[C.c_uint32,C.c_double,C.POINTER(Model),D]
        self.dll.e1_default_options.argtypes=[C.POINTER(Options)]
        self.dll.e1_evaluate_xyz.argtypes=[C.POINTER(Model),C.POINTER(Options),C.c_uint64,D,D,D,U8,C.POINTER(Output)]
        node_args=[C.POINTER(Model),C.POINTER(Options),C.POINTER(Plane),C.POINTER(Window),C.c_uint32,U64,C.c_uint64,U8,C.POINTER(Output)]
        self.dll.e1_evaluate_nodes.argtypes=node_args
        self.dll.e1_timed_nodes.argtypes=node_args+[D]
        self.dll.e1_forward_batch.argtypes=[C.c_uint32,C.c_uint64,D,D,D,D,D,D,D]
        self.dll.e1_noop.argtypes=[];self.dll.e1_noop.restype=None

    def model(self,name='nonlinear_high',radius=1/64):
        model=Model();holes=np.empty(12,np.float64)
        self.dll.e1_default_model(MODELS[name],radius,C.byref(model),holes.ctypes.data_as(D))
        model._holes_keepalive=holes
        return model

    def options(self):
        out=Options();self.dll.e1_default_options(C.byref(out));return out

    def xyz(self,points,name='nonlinear_high',radius=1/64,options=None,forced=None):
        points=np.asarray(points,dtype=np.float64).reshape(-1,3)
        xyz=[np.ascontiguousarray(points[:,k]) for k in range(3)]
        arrays,out=allocate(len(points));model=self.model(name,radius);opt=options or self.options()
        flags=None if forced is None else np.ascontiguousarray(forced,dtype=np.uint8)
        if flags is not None and len(flags)!=len(points):raise ValueError('Failure flags length')
        rc=self.dll.e1_evaluate_xyz(C.byref(model),C.byref(opt),len(points),*[v.ctypes.data_as(D) for v in xyz],
            None if flags is None else flags.ctypes.data_as(U8),C.byref(out))
        if rc:raise ValueError('Invalid batch configuration')
        return arrays

    def node_buffers(self,n,name='nonlinear_high',radius=1/64,ids=None,window=None,plane=None):
        ids=None if ids is None else np.ascontiguousarray(ids,dtype=np.uint64)
        count=(n+1)**2 if ids is None else len(ids)
        arrays,out=allocate(count);model=self.model(name,radius);opt=self.options()
        window=window or [[-.125,-.125],[1.125,1.125]]
        plane=plane or [[0,0,.52],[1,0,0],[0,1,0]]
        p=Plane(*[(C.c_double*3)(*a) for a in plane]);w=Window(*[(C.c_double*2)(*a) for a in window])
        args=(C.byref(model),C.byref(opt),C.byref(p),C.byref(w),n,None if ids is None else ids.ctypes.data_as(U64),count,None,C.byref(out))
        # Explicit lifetimes for every buffer referenced through C pointers.
        return dict(arrays=arrays,args=args,keepalive=(out,model,opt,p,w,ids))

    def nodes(self,buffers,timed=False):
        seconds=C.c_double()
        rc=self.dll.e1_timed_nodes(*buffers['args'],C.byref(seconds)) if timed else self.dll.e1_evaluate_nodes(*buffers['args'])
        if rc:raise ValueError('Invalid batch configuration')
        return seconds.value if timed else buffers['arrays']

    def forward(self,points,name):
        xyz=[np.ascontiguousarray(np.asarray(points)[:,k],dtype=np.float64) for k in range(3)]
        out=[np.empty(len(xyz[0]),np.float64) for _ in range(3)];j=np.empty((len(xyz[0]),3,3),np.float64)
        rc=self.dll.e1_forward_batch(MODELS[name],len(xyz[0]),*[v.ctypes.data_as(D) for v in xyz+out],j.ctypes.data_as(D))
        if rc:raise ValueError('Invalid forward batch')
        return np.column_stack(out),j
