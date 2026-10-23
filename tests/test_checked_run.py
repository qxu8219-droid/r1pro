import subprocess,sys,tempfile,unittest
from pathlib import Path
SCRIPT=Path(__file__).resolve().parents[1]/'scripts/run_checked.py'
class CheckedRunTests(unittest.TestCase):
    def run_case(self,payload,expected,stale=False):
        self.assertTrue(SCRIPT.is_file(),'checked launcher missing')
        with tempfile.TemporaryDirectory() as d:
            report=Path(d)/'result.json'
            if stale: report.write_text('{"status":"pass"}')
            code='pass' if stale else f'from pathlib import Path; Path({str(report)!r}).write_text({payload!r})'
            p=subprocess.run([sys.executable,str(SCRIPT),'--report',str(report),'--',sys.executable,'-c',code],capture_output=True,text=True)
            self.assertEqual(p.returncode,expected,p.stdout+p.stderr)
    def test_report_failure_overrides_zero_process_exit(self):self.run_case('{"status":"fail"}',1)
    def test_stale_pass_is_not_accepted(self):self.run_case('',1,True)
    def test_fresh_pass_is_accepted(self):self.run_case('{"status":"pass"}',0)
if __name__=='__main__':unittest.main()
