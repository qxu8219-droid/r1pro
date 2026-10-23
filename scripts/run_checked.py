"""Check fresh structured evidence as well as process status (Kit may exit early)."""
import argparse,json,subprocess,time
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('--report',type=Path,required=True);ap.add_argument('--timeout',type=float,default=300);ap.add_argument('--accept',default='pass');ap.add_argument('command',nargs=argparse.REMAINDER)
a=ap.parse_args();cmd=a.command[1:] if a.command[:1]==['--'] else a.command
if not cmd:ap.error('command required after --')
before=a.report.stat().st_mtime_ns if a.report.exists() else None
try:
    process=subprocess.run(cmd,timeout=a.timeout)
    if process.returncode:raise RuntimeError(f'process exited {process.returncode}')
    if not a.report.exists() or a.report.stat().st_mtime_ns==before:raise RuntimeError('missing or stale report')
    result=json.loads(a.report.read_text())
    if result.get('status')!=a.accept:raise RuntimeError(f'report status: {result.get("status")}')
except (OSError,ValueError,RuntimeError,subprocess.TimeoutExpired) as e:
    print(f'CHECKED_RUN_FAILED: {e}',flush=True);raise SystemExit(1)
print(f'CHECKED_RUN_PASS: {a.report}',flush=True)
