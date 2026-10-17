"""Resume only ledger/archive bookkeeping after correcting a stale round-number assertion."""
from common import *

assert os.environ.get('SLURM_JOB_ID')
change = json.loads(ROOT.joinpath('change.json').read_text())
validation = json.loads(ROOT.joinpath('validation.json').read_text())
candidate = change['candidate']
worktree = Path(candidate['worktree_path'])
assert change['round'] == 16 and change['state'] == 'validated_awaiting_deployment_approval'
assert len(validation['checks']) == 31 and all(validation['checks'].values())
assert git(worktree, 'rev-parse', 'HEAD') == change['candidate_commit'] == '18c0ae3d6af0baf151487681aac40d7a09dd475c'
assert git(worktree, 'rev-parse', 'HEAD^{tree}') == change['candidate_tree']
assert not git(worktree, 'status', '--porcelain')
assert git(PRODUCTION, 'rev-parse', 'HEAD') == change['current_production_commit']
assert not git(PRODUCTION, 'status', '--porcelain')
pool_path = INSTANCE / 'candidate-pool.json'
pool = json.loads(pool_path.read_text())
before = json.loads(ROOT.joinpath('candidate-pool-before.json').read_text())
assert pool['current_round'] == 16 and pool['selected_candidate_id'] == SELECTED
assert pool['history'] == before['history'] and all(p in pool['proposals'] for p in before['proposals'])
selected = next(p for p in pool['proposals'] if p['id'] == SELECTED)
assert selected['status'] == 'selected_preparing' and selected['measured'] is False
selected.update({'status': change['state'], 'candidate_commit': change['candidate_commit'],
    'candidate_tree': change['candidate_tree'], 'wrapper_run_id': change['wrapper_run_id'], 'branch': candidate['branch']})
write('candidate-pool-after.json', pool)
write('preparation-recovery.json', {
    'initial_job': 1816002, 'initial_exit': 1,
    'cause': 'After all 31 checks and the candidate commit, a reused ledger assertion incorrectly expected current_round 15 instead of 16.',
    'fix': 'Corrected candidate_r16.py assertion to round 16 and resumed only the remaining ledger/archive steps.',
    'same_run_id': change['wrapper_run_id'], 'same_candidate_commit': change['candidate_commit'],
    'all_31_checks_passed_before_recovery': True,
    'new_candidate_allocated': False, 'candidate_rewritten': False, 'old_history_changed': False})
pool_path.write_text(json.dumps(pool, ensure_ascii=False, indent=2) + '\n')
print('R16 ledger bookkeeping resumed; run, candidate, production and old proposals unchanged.')
