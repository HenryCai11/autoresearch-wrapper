"""Use only real registered live results to evaluate and record the existing run."""
import sys
from common import *

assert os.environ.get('SLURM_JOB_ID')
LIVE = ROOT / 'r21-live'
run = json.loads(ROOT.joinpath('wrapper-run.json').read_text())
summary = json.loads(LIVE.joinpath('summary.json').read_text())
assert summary['scheduled']['valid_responses'] == 60

def live_cli(*args, name):
    environment = os.environ.copy()
    environment.pop('PYTHONPATH', None)
    result = subprocess.run(['bash', str(RUNNER), *args, '--repo', str(SITE)], env=environment, capture_output=True, text=True)
    LIVE.joinpath(name).write_text(result.stdout)
    LIVE.joinpath(name + '.stderr.txt').write_text(result.stderr)
    if result.returncode:
        print(result.stderr, file=sys.stderr)
        result.check_returncode()
    return json.loads(result.stdout)

resumed = live_cli('run', '--part', 'index.html', '--no-interactive', '--json', name='wrapper-resume.json')
assert resumed['run_id'] == run['run_id'], 'Do not start a different R21 run'
evaluation = live_cli('evaluate', '--run-id', run['run_id'], '--candidate', 'candidate-001', '--json', name='wrapper-evaluation.json')
record = live_cli('record', '--run-id', run['run_id'], '--candidate', 'candidate-001', '--status', 'auto',
    '--description', 'R21 exact retained R14 static table on R18; discarded R20 H1s not inherited; exact deployed tree and three changed served pages verified; 60 frozen outer cells; R18 12/60 historical control; parent scores not added',
    '--json', name='wrapper-record.json')
assert record['status'] == summary['decision']
live_cli('status', '--json', name='wrapper-status.json')
print(json.dumps({'evaluation': evaluation, 'record': record}, indent=2))
