"""Record only the original R18 control; allocate one R21 worktree."""
from common import *

assert os.environ.get('SLURM_JOB_ID')
assert not ROOT.joinpath('wrapper-candidate.json').exists(), 'Do not allocate twice'
run = json.loads(ROOT.joinpath('wrapper-run.json').read_text())
cli('evaluate','--run-id',run['run_id'],'--candidate','seed','--json',name='seed-evaluation.json')
record = json.loads(cli('record','--run-id',run['run_id'],'--candidate','seed','--status','auto',
    '--description','Original R18 12/60 historical control; not R20 or new R21 searches','--json',name='seed-record.json'))
assert record['metric_value'] == 20.0
candidate = json.loads(cli('allocate','--run-id',run['run_id'],'--json',name='wrapper-candidate.json'))
worktree = Path(candidate['worktree_path'])
for command,name in [('geo-graph','graph-before.json'),('geo-prioritize','priorities.json'),('geo-decide','decision.json'),('geo-explore','exploration.json')]:
    args = [command,'--config',str(ROOT / 'config.json')]
    if command != 'geo-graph':
        args += ['--search-evidence',str(ROOT / 'r20-search-evidence.json')]
    cli(*args,name=name,repo=worktree)
write('edit-mechanism.json',{'operations':1,'method':'Existing geo-apply replace_text on supported file:index.html in allocated worktree',
    'manifest':'Exact retained final R14 operations.json; only the original insertion, no rewrite',
    'graph_nodes':['file:index.html','section:results'],'wrapper_core_changed':False,'production_changed':False})
print(json.dumps({'candidate':candidate,'seed_metric':record['metric_value'],'pending_geo_apply_operations':1},indent=2))
