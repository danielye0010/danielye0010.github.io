"""Run native/reference tests included with the public source distribution."""
from pathlib import Path
import argparse,importlib.util,sys,unittest
ROOT=Path(__file__).resolve().parents[1]
path=ROOT/'course_project/gpu/e1/tests/test_native.py'
spec=importlib.util.spec_from_file_location('native_tests',path)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
parser=argparse.ArgumentParser();parser.add_argument('--library',required=True);args=parser.parse_args()
module.LIB=args.library
# Full E0 replay data remain in the research archive. Core tests use the
# unchanged original Python implementation, shipped with this distribution.
module.NativeTests.test_saved_e0_primary_samples=unittest.skip('Full E0 replay archive is not part of this source distribution')(module.NativeTests.test_saved_e0_primary_samples)
suite=unittest.defaultTestLoader.loadTestsFromTestCase(module.NativeTests)
result=unittest.TextTestRunner(verbosity=2).run(suite)
raise SystemExit(0 if result.wasSuccessful() else 1)
