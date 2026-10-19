"""Record the original R18 control and allocate one reference-heading candidate."""
from common import *

assert os.environ.get('SLURM_JOB_ID')
assert not ROOT.joinpath('wrapper-candidate.json').exists(), 'Do not allocate twice'
run = json.loads(ROOT.joinpath('wrapper-run.json').read_text())
cli('evaluate','--run-id',run['run_id'],'--candidate','seed','--json',name='seed-evaluation.json')
record = json.loads(cli('record','--run-id',run['run_id'],'--candidate','seed','--status','auto',
    '--description','Original R18 12/60 historical control; not R19 or new R20 searches','--json',name='seed-record.json'))
assert record['metric_value'] == 20.0
candidate = json.loads(cli('allocate','--run-id',run['run_id'],'--json',name='wrapper-candidate.json'))
worktree = Path(candidate['worktree_path'])
for command,name in [('geo-graph','graph-before.json'),('geo-prioritize','priorities.json'),('geo-decide','decision.json'),('geo-explore','exploration.json')]:
    args = [command,'--config',str(ROOT / 'config.json')]
    if command != 'geo-graph':
        args += ['--search-evidence',str(ROOT / 'r19-search-evidence.json')]
    cli(*args,name=name,repo=worktree)
write('edit-mechanism.json',{'operations':2,'method':'Main-agent apply_patch in this allocated worktree',
    'graph_nodes':['file:method.html','file:research-context.html'],
    'limitation':'Existing graph exposes linked HTML as fingerprinted asset nodes with no text mutation operations; geo-apply is not used or claimed for these two edits.',
    'wrapper_core_changed':False,'production_changed':False})
print(json.dumps({'candidate':candidate,'seed_metric':record['metric_value'],'pending_apply_patch_operations':2},indent=2))
