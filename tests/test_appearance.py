import importlib.util
from pathlib import Path
import unittest
import numpy as np
SCRIPT=Path(__file__).resolve().parents[1]/'scripts/appearance.py'
class AppearanceTests(unittest.TestCase):
    def fn(self):
        self.assertTrue(SCRIPT.exists(),'UV mapper not implemented')
        spec=importlib.util.spec_from_file_location('appearance',SCRIPT);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
        return m.match_triangle_uv
    def test_reordered_triangle_preserves_corner_uv(self):
        points=np.array([[[0,0,0],[1,0,0],[0,1,0]]],float);uv=np.array([[[0,0],[1,0],[0,1]]],float)
        mapped,valid=self.fn()(points,uv,points[:,[2,0,1],:])
        np.testing.assert_allclose(mapped,uv[:,[2,0,1],:]);self.assertTrue(valid.all())
    def test_changed_geometry_has_no_false_match(self):
        p=np.array([[[0,0,0],[1,0,0],[0,1,0]]],float)
        _,valid=self.fn()(p,np.zeros((1,3,2)),p+1)
        self.assertFalse(valid.any())
    def test_conflicting_uv_on_same_triangle_is_rejected(self):
        p=np.array([[[0,0,0],[1,0,0],[0,1,0]]],float)
        _,valid=self.fn()(np.concatenate([p,p]),np.concatenate([np.zeros((1,3,2)),np.ones((1,3,2))]),p)
        self.assertFalse(valid.any())
if __name__=='__main__':unittest.main()
