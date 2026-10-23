import importlib.util
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET

SCRIPT=Path(__file__).resolve().parents[1]/'scripts/source_audit.py'
BASE=Path(__file__).resolve().parents[1]/'deliverables/r1pro_2026_vendor_sources_20261022'

class AuditTests(unittest.TestCase):
    def audit(self, path):
        self.assertTrue(SCRIPT.is_file(), 'source audit tool has not been implemented')
        spec=importlib.util.spec_from_file_location('audit',SCRIPT)
        mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
        return mod.audit_urdf(path,BASE/'sdk/r1pro_urdf/share/r1pro_urdf')

    def test_vendor_tree_and_unrated_wheels(self):
        r=self.audit(BASE/'sdk/r1pro_urdf/share/r1pro_urdf/urdf/r1pro_2026.urdf')
        self.assertEqual(len(r['links']),46)
        self.assertEqual(len(r['moving_joints']),28)
        self.assertEqual(r['root_links'],['base_link'])
        self.assertEqual(r['errors'],[])
        self.assertEqual(sum(w['code']=='missing_effort_velocity' for w in r['warnings']),3)

    def test_invalid_inertia_is_rejected(self):
        tree=ET.parse(BASE/'sdk/r1pro_urdf/share/r1pro_urdf/urdf/r1pro_2026.urdf')
        tree.find('link/inertial/inertia').set('ixx','-1')
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'bad.urdf'; tree.write(p)
            r=self.audit(p)
            self.assertTrue(any(e['code']=='invalid_inertia' for e in r['errors']))

    def test_missing_mesh_is_rejected(self):
        tree=ET.parse(BASE/'sdk/r1pro_urdf/share/r1pro_urdf/urdf/r1pro_2026.urdf')
        tree.find('.//mesh').set('filename','package://r1pro_urdf/meshes/absent.STL')
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'bad.urdf'; tree.write(p)
            r=self.audit(p)
            self.assertTrue(any(e['code']=='missing_mesh' for e in r['errors']))

if __name__=='__main__': unittest.main()
