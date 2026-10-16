"""Evaluate/record only after real live observations have been registered."""
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LIVE = ROOT / 'r13-live'
SITE = Path('/scratch/henrycai/eau-r13-20261016')
run = json.loads(ROOT.joinpath('wrapper-run.json').read_text())
summary = json.loads(LIVE.joinpath('summary.json').read_text())
assert summary['scheduled']['valid_responses'] == 60, 'Incomplete run must remain unranked'


def cli(*args, name):
    environment = os.environ.copy()
    environment.pop('PYTHONPATH', None)
    result = subprocess.run(['bash', '/project/aip-xiye17/henrycai/autoresearch-wrapper/skills/autoresearch-wrapper-run/run.sh',
                             *args, '--repo', str(SITE)], env=environment, capture_output=True, text=True)
    LIVE.joinpath(name).write_text(result.stdout)
    LIVE.joinpath(name + '.stderr.txt').write_text(result.stderr)
    if result.returncode:
        print(result.stderr, file=sys.stderr)
        result.check_returncode()
    return json.loads(result.stdout)


resumed = cli('run', '--part', 'index.html', '--no-interactive', '--json', name='wrapper-resume.json')
assert resumed['run_id'] == run['run_id'], 'Do not start a different R13 run'
evaluation = cli('evaluate', '--run-id', run['run_id'], '--candidate', 'candidate-001', '--json', name='wrapper-evaluation.json')
record = cli('record', '--run-id', run['run_id'], '--candidate', 'candidate-001', '--status', 'auto',
             '--description', 'R13 static environment and agent reference on best R9 seed; exact deployed tree and homepage bytes verified; 60 frozen outer cells; R9 8/60 control',
             '--json', name='wrapper-record.json')
assert record['status'] == summary['decision']
cli('status', '--json', name='wrapper-status.json')
print(json.dumps({'evaluation': evaluation, 'record': record}, indent=2))
