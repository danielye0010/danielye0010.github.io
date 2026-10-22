from pathlib import Path
import argparse,ctypes as C,itertools,json,sys,unittest
import numpy as np
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parents[2]
sys.path.insert(0,str(PROJECT));sys.path.insert(0,str(ROOT))
from native import Native,MODELS,allocate
from solid_modeling import AnalyticCSG,Deformation
from solid_modeling.deformation import engine
LIB=None


class NativeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.native=Native(LIB)

    def assert_parity(self,y,name='nonlinear_high',radius=1/64):
        m=Deformation(name);body=AnalyticCSG().with_last_radius(radius)
        x,r,detail=engine.solve(m.model,y);value=body.value(x)
        out=self.native.xyz(y,name,radius)
        xx=np.column_stack([out['source_x'],out['source_y'],out['source_z']])
        self.assertTrue((out['numeric_status']==1).all())
        self.assertLessEqual(float(np.max(out['residual_inf'],initial=0)),3e-13)
        np.testing.assert_allclose(xx,x,rtol=0,atol=5e-12)
        np.testing.assert_allclose(out['value'],value,rtol=0,atol=5e-12)
        _,_,bound=m.model.bound(r)
        np.testing.assert_array_equal(out['guarded_sign'],engine.labels(value,bound))
        return out

    def test_default_geometry_and_abi(self):
        m=self.native.model();s=AnalyticCSG()
        np.testing.assert_array_equal(m._holes_keepalive.reshape(-1,3),s.holes)
        np.testing.assert_array_equal(m.lo,s.lo);np.testing.assert_array_equal(m.hi,s.hi)
        self.assertEqual(self.native.dll.e1_abi_version(),1)

    def test_forward_jacobian_fe_interfaces_exterior(self):
        rng=np.random.default_rng(20261022)
        knots=np.array(list(itertools.product([0.,.25,.5,.75,1.],repeat=3)))
        points=np.r_[rng.uniform(-.5,1.5,(256,3)),knots,np.nextafter(knots,-np.inf),np.nextafter(knots,np.inf)]
        for name in MODELS:
            m=Deformation(name);f,j=self.native.forward(points,name)
            np.testing.assert_allclose(f,m.forward_reference(points),rtol=0,atol=2e-14)
            np.testing.assert_allclose(j,m.jacobian(points),rtol=0,atol=2e-14)

    def test_random_inverses_all_models(self):
        x=np.random.default_rng(12).uniform(-.5,1.5,(1024,3))
        for name in MODELS:self.assert_parity(Deformation(name).forward_reference(x),name)

    def test_boundaries_near_zero_and_small_hole(self):
        body=AnalyticCSG().with_last_radius(1/256)
        p=list(itertools.product([0.,1/16,.25,.5,.75,15/16,1.],repeat=3))
        for h in body.holes:
            for theta in np.linspace(0,2*np.pi,48,endpoint=False):
                for eps in [-1e-12,0,1e-12]:p.append([h[0]+(h[2]+eps)*np.cos(theta),h[1]+(h[2]+eps)*np.sin(theta),.52])
        for name in MODELS:self.assert_parity(Deformation(name).forward_reference(np.array(p)),name,1/256)

    def test_no_interval_qualification(self):
        out=self.assert_parity(np.array([[.1,.2,.52],[.5,.5,.52]]))
        self.assertTrue((out['qualification']==0).all());self.assertTrue(np.isneginf(out['field_lower']).all())
        self.assertTrue(np.isposinf(out['field_upper']).all());self.assertTrue(np.isposinf(out['inverse_error_inf']).all())
        self.assertTrue((out['failure_reason']==5).all())

    def test_nonfinite_and_failure_controls(self):
        y=np.array([[.1,.2,.3],[np.nan,0,0],[0,np.inf,0],[0,0,-np.inf]])
        out=self.native.xyz(y)
        np.testing.assert_array_equal(out['numeric_status'],[1,3,3,3])
        self.assertTrue(np.isnan(out['value'][1:]).all());self.assertTrue((out['guarded_sign'][1:]==0).all())
        out=self.native.xyz(np.array([[.1,.2,.3],[.3,.4,.5]]),forced=[0,1])
        np.testing.assert_array_equal(out['numeric_status'],[1,8])

    def test_iteration_failure_matches_original_final_check(self):
        y=np.random.default_rng(1).uniform(.1,.9,(32,3));m=Deformation('nonlinear_high')
        opt=self.native.options();opt.max_iterations=0
        out=self.native.xyz(y,options=opt)
        expected=[]
        for p in y:
            try:engine.solve(m.model,p[None,:],stop=np.inf);expected.append(1)
            except RuntimeError:expected.append(2)
        np.testing.assert_array_equal(out['numeric_status'],expected)
        self.assertTrue((out['qualification']==0).all())

    def test_field_tolerance_and_unsupported_map(self):
        opt=self.native.options();opt.field_tolerance=1e-16
        y=np.array([[.3,.4,.5]])
        out=self.native.xyz(y,options=opt);self.assertEqual(out['numeric_status'][0],6)
        with self.assertRaises(ValueError):Deformation('nonlinear_high').inverse(y,field_tolerance=1e-16)
        b=self.native.node_buffers(4);b['keepalive'][1].model_id=999;self.native.nodes(b)
        self.assertTrue((b['arrays']['numeric_status']==4).all())

    def test_lattice_order_invalid_ids_and_empty(self):
        n=64;ids=np.array([0,4224,55,55,200,4225],dtype=np.uint64)
        b=self.native.node_buffers(n,ids=ids);self.native.nodes(b)
        out=b['arrays'];self.assertEqual(out['numeric_status'][-1],5)
        uv=-.125+1.25*np.column_stack([ids[:-1]%65,ids[:-1]//65])/64
        ref=self.native.xyz(np.column_stack([uv,np.full(len(uv),.52)]))
        np.testing.assert_array_equal(out['value'][:-1],ref['value'])
        self.assertEqual(self.native.dll.e1_evaluate_xyz(None,None,0,None,None,None,None,None),0)

    def test_saved_e0_primary_samples(self):
        base=PROJECT/'course_project/gpu/e0/results/run_20261021_complete'
        for case,radius in [('strong_four_hole',1/64),('strong_small_hole',1/256)]:
            with np.load(base/case/'1024_global/samples.npz') as z:
                ix=np.linspace(0,len(z['node_ids'])-1,4096,dtype=int);ids=z['node_ids'][ix];values=z['value'][ix]
            b=self.native.node_buffers(1024,ids=ids,radius=radius);self.native.nodes(b)
            np.testing.assert_allclose(b['arrays']['value'],values,rtol=0,atol=5e-12)
            self.assertTrue((b['arrays']['numeric_status']==1).all())


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--library');args,rest=parser.parse_known_args();LIB=args.library
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(NativeTests)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    (ROOT/'results/unit_tests.json').write_text(json.dumps(dict(tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),passed=result.wasSuccessful()),indent=2))
    raise SystemExit(0 if result.wasSuccessful() else 1)
