"""Record only the original R18 historical control; allocate one R22 candidate."""
from common import *
assert os.environ.get('SLURM_JOB_ID')
assert not ROOT.joinpath('wrapper-candidate.json').exists(), 'Do not allocate twice'
run = json.loads(ROOT.joinpath('wrapper-run.json').read_text())
cli('evaluate','--run-id',run['run_id'],'--candidate','seed','--json',name='seed-evaluation.json')
record = json.loads(cli('record','--run-id',run['run_id'],'--candidate','seed','--status','auto',
    '--description','Original R18 12/60 historical control; not R21 or new R22 searches','--json',name='seed-record.json'))
assert record['metric_value'] == 20.0
candidate = json.loads(cli('allocate','--run-id',run['run_id'],'--json',name='wrapper-candidate.json'))
worktree = Path(candidate['worktree_path'])
for command,name in [('geo-graph','graph-before.json'),('geo-prioritize','priorities.json'),('geo-decide','decision.json'),('geo-explore','exploration.json')]:
    args = [command,'--config',str(ROOT / 'config.json')]
    if command != 'geo-graph':
        args += ['--search-evidence',str(ROOT / 'r21-search-evidence.json')]
    cli(*args,name=name,repo=worktree)
graph = json.loads(ROOT.joinpath('graph-before.json').read_text())
node = next(n for n in graph['nodes'] if n['id'] == 'file:paper.html')
assert node['operations'] == []
write('edit-mechanism.json',{'semantic_changes':1,'text_spans':2,'method':'Main-agent apply_patch in allocated worktree after reading generated program.md',
    'graph_nodes':['file:paper.html'],'graph_supported_operations':node['operations'],
    'limit':'No geo-apply operation is claimed for support assets; no wrapper-core extension',
    'wrapper_core_changed':False,'production_changed':False})
print(json.dumps({'candidate':candidate,'seed_metric':record['metric_value'],'edit_method':'apply_patch, not geo-apply'},indent=2))
