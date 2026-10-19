"""Record historical R18 seed and allocate one combination candidate."""
from common import *

assert os.environ.get('SLURM_JOB_ID')
assert not ROOT.joinpath('wrapper-candidate.json').exists(), 'Do not allocate twice'
run = json.loads(ROOT.joinpath('wrapper-run.json').read_text())
cli('evaluate','--run-id',run['run_id'],'--candidate','seed','--json',name='seed-evaluation.json')
record = json.loads(cli('record','--run-id',run['run_id'],'--candidate','seed','--status','auto',
    '--description','Preserved R18 12/60 historical control; no new R19 searches','--json',name='seed-record.json'))
assert record['metric_value'] == 20.0
candidate = json.loads(cli('allocate','--run-id',run['run_id'],'--json',name='wrapper-candidate.json'))
worktree = Path(candidate['worktree_path'])
for command,name in [('geo-graph','graph-before.json'),('geo-prioritize','priorities.json'),
    ('geo-decide','decision.json'),('geo-explore','exploration.json')]:
    args = [command,'--config',str(ROOT / 'config.json')]
    if command != 'geo-graph':
        args += ['--search-evidence',str(ROOT / 'r18-search-evidence.json')]
    cli(*args,name=name,repo=worktree)
for apply,name in [(False,'preview.json'),(True,'applied.json')]:
    args = ['geo-apply','--config',str(ROOT / 'config.json'),'--operations',str(ROOT / 'wrapper-operations.json')]
    if apply:
        args.append('--apply')
    cli(*args,name=name,repo=worktree)
print(json.dumps({'candidate':candidate,'graph_operations_applied':1,'pending_apply_patch_operations':3},indent=2))
