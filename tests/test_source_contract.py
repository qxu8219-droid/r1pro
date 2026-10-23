import importlib.util,unittest,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];SCRIPT=ROOT/'scripts/source_contract.py';SOURCE=ROOT/'deliverables/r1pro_2026_vendor_sources_20261022'
class ContractTests(unittest.TestCase):
    def module(self):
        self.assertTrue(SCRIPT.exists(),'source contract not implemented')
        s=importlib.util.spec_from_file_location('contract',SCRIPT);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
    def test_original_source_is_accepted(self):
        m=self.module();selected=m.verify_source(SOURCE);self.assertEqual(selected['selected_model_sha256'],m.EXPECTED_URDF_SHA256)
    def test_modified_selection_is_rejected(self):
        m=self.module()
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'SELECTED_MODEL.json').write_text('{}')
            with self.assertRaisesRegex(ValueError,'selection'):m.verify_source(p)
    def test_nonempty_output_is_rejected_without_modification(self):
        m=self.module()
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'old.usd').write_text('preserve')
            with self.assertRaisesRegex(ValueError,'empty'):m.require_fresh_output(p,SOURCE)
            self.assertEqual((p/'old.usd').read_text(),'preserve')
    def test_vendor_subdirectory_cannot_be_output(self):
        with self.assertRaisesRegex(ValueError,'source'):self.module().require_fresh_output(SOURCE/'new_output',SOURCE)
if __name__=='__main__':unittest.main()
