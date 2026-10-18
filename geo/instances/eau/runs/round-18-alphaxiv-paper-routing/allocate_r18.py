"""Record the historical seed and allocate one isolated routing candidate."""
from common import *

assert os.environ.get('SLURM_JOB_ID')
assert not ROOT.joinpath('wrapper-candidate.json').exists(), 'Do not allocate a second R18 candidate'
run = json.loads(ROOT.joinpath('wrapper-run.json').read_text())
cli('evaluate', '--run-id', run['run_id'], '--candidate', 'seed', '--json', name='seed-evaluation.json')
seed = json.loads(cli('record', '--run-id', run['run_id'], '--candidate', 'seed', '--status', 'auto',
    '--description', 'Preserved best R17 10/60 historical control; not new R18 searches', '--json', name='seed-record.json'))
assert abs(seed['metric_value'] - 100 * 10 / 60) < 1e-9
candidate = json.loads(cli('allocate', '--run-id', run['run_id'], '--json', name='wrapper-candidate.json'))
worktree = Path(candidate['worktree_path'])
config, evidence = str(ROOT / 'config.json'), str(ROOT / 'r17-search-evidence.json')
for command, output in [('geo-graph', 'graph-before.json'), ('geo-prioritize', 'priorities.json'),
                        ('geo-decide', 'decision.json'), ('geo-explore', 'exploration.json')]:
    args = [command, '--config', config]
    if command != 'geo-graph':
        args += ['--search-evidence', evidence]
    cli(*args, name=output, repo=worktree)
cli('geo-apply', '--config', config, '--operations', str(ROOT / 'wrapper-operations.json'), name='preview.json', repo=worktree)
cli('geo-apply', '--config', config, '--operations', str(ROOT / 'wrapper-operations.json'), '--apply', name='applied.json', repo=worktree)
print(json.dumps({'candidate': candidate, 'applied_graph_operations': 5, 'pending_apply_patch_operations': 4,
    'instruction': 'Apply manual-operations.json exact replacements using apply_patch, then validate and archive; do not score or record unpublished candidate'}, indent=2))
