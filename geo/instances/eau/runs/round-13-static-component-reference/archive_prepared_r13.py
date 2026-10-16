"""Archive and replay the unmeasured R13 candidate without modifying production."""
import re
import shutil
import sys
from common import *

assert os.environ.get('SLURM_JOB_ID')
change = json.loads(ROOT.joinpath('change.json').read_text())
validation = json.loads(ROOT.joinpath('validation.json').read_text())
context = json.loads(ROOT.joinpath('production-context.json').read_text())
run = json.loads(ROOT.joinpath('wrapper-run.json').read_text())
pool = json.loads(INSTANCE.joinpath('candidate-pool.json').read_text())
before = json.loads(ROOT.joinpath('candidate-pool-before.json').read_text())
assert change['state'] == 'validated_awaiting_deployment_approval' and all(validation['checks'].values())
assert not DEST.exists(), 'Append-only archive refuses overwrite'
assert pool['history'] == before['history'] and len(pool['history']) == 13
assert all(p in pool['proposals'] for p in before['proposals'] if p['id'] != SELECTED)
selected = next(p for p in pool['proposals'] if p['id'] == SELECTED)
assert selected['original_proposal'] == next(p for p in before['proposals'] if p['id'] == SELECTED)
assert len(pool['proposals']) == len(before['proposals']) == 8 and not selected['measured']
assert len([p for p in pool['proposals'] if not p.get('measured', False)]) == 3
assert git(PRODUCTION, 'rev-parse', 'HEAD') == change['current_production_commit']
assert not git(PRODUCTION, 'status', '--porcelain')
registry = json.loads(ROOT.joinpath('outer-measurements.json').read_text())
assert len(registry['measurements']) == 1
registry['measurements'][0]['matrix'] = os.path.relpath(Path(context['seed_measurement_dir']) / 'search-matrix.csv', DEST)
write('portable-outer-measurements.json', registry)
evidence = json.loads(ROOT.joinpath('r12-search-evidence.json').read_text())
for item in evidence['observations']:
    item['raw_file'] = '../round-12-homepage-descriptive-h1/r12-live/gpt-web-answers.jsonl'
    item['raw_files'] = {engine: '../round-12-homepage-descriptive-h1/r12-live/' + Path(name).name
                         for engine,name in item['raw_files'].items()}
write('portable-search-evidence.json', evidence)
ROOT.joinpath('README.md').write_text(f'''# EAU R13 — static component reference

Status: **validated local candidate; not published or measured**.

- Wrapper run: {run['run_id']}; sequential, one candidate.
- Pool proposal: static-component-reference, previously queued and unmeasured.
- Candidate commit: {change['candidate_commit']}.
- Candidate tree: {change['candidate_tree']}.
- Selection seed: best recorded R{context['selection_seed_round']},
  {context['seed_observation']['project_citations']}/60 citations; preserved
  historical control, not newly collected or simultaneous.
- Production remains R12 {change['current_production_commit']},
  6/60 citations, composite 29.28, discard; no automatic rollback.

## One focused intervention

Only index.html differs from the seed. In its existing framework section, add
two persistent semantic article blocks for the environment and agent, copying
their titles, descriptions and three knob labels each verbatim from script.js.
The default user description is not duplicated. The original interactive tabs,
panel, diagram, timescales and every other named section are unchanged. Existing
timescales and knob-list styles are reused; no script, CSS, metadata, links,
benchmark numbers or method claims are added or changed.

The selected seed is R9 because R12 did not beat its 8/60 primary threshold.
Therefore R13 does not silently carry forward R12's H1, R11's overview restoration
or R10's JSON-LD change. Those candidates and all R0–R12 observations remain in
the ledger for future combinations. Relative to current R12 production,
index.html contains both the static descriptions and the return to R9's H1.

The latest actual responses contain 3 explicit project URL cells and no support
page URLs. This identifies an observed homepage entry surface, not a predicted
static-text ranking gain. The environment/agent descriptions currently require
a tab interaction; this test exposes only that existing information in source
HTML. R12 lost two frozen citation cells versus R9, with no gains; that immediate
sample does not establish that the H1 caused either loss.

## Cross-module and history safeguards

module-review.json records the nine-module review. The full 13-entry R0–R12
history and all eight proposals remain; seven non-selected proposals are
unchanged and the original selected proposal is nested in its updated entry.
The second-backbone static-evidence proposal stays queued. The external paper
backlink state remains unknown, and editing it requires separate author
authority. All three unmeasured proposals remain unscored; parent observations
are never added to predict combinations.

## Validation and measurement gate

All {len(validation['checks'])} local structural/factual checks passed. Visible
homepage text: {validation['visible_home_chars_before']} →
{validation['visible_home_chars_after']} characters, under the unchanged
{validation['limit']} limit. No inner score was computed. Validation covers
verbatim source text, exact one-insertion scope, preserved interactive markup,
all links/IDs, unchanged JSON-LD/results, and frozen map/query/judge/normalizer
hashes. No browser or visual test was performed; rendered behavior is not claimed.

The exact-tree metric guard rejects this unpublished candidate. Publishing R13
requires separate explicit user approval. Apply the exact candidate index.html
in an isolated deploy branch based on current main, verify the entire candidate
tree, then verify served bytes before collection and after **all** 60 responses
have finished. Do not blindly merge a historical-seed branch into production.
Reconcile any concurrent teammate changes before proceeding.

After approval, use the same 15 queries × GPT web / Codex / Tavily / Exa settings.
Require all 60 valid cells and strictly more than 8/60 frozen project-domain
citation cells for keep; ties discard. The judge includes bare domain
occurrences, so report explicit source URLs separately. This is not consumer
chat-app evidence, and one immediate sample against a historical control cannot
establish causality or exclude indexing delay.

This preparation used Slurm (one CPU, 1 GB). It did not publish, push a site
branch, collect R13 search responses, schedule a follow-up, prune candidates
or alter production. Prepared files are durable instance records; scratch
worktrees are not the only copy of the intervention and evidence.
''')
names = ['README.md', 'change.json', 'production-context.json', 'validation.json',
    'static-component-source.json', 'operations.json', 'candidate.patch', 'production-to-candidate.patch',
    'module-review.json', 'config.json', 'graph-before.json', 'graph-after.json', 'priorities.json',
    'decision.json', 'exploration.json', 'preview.json', 'applied.json',
    'candidate-pool-before.json', 'candidate-pool-selected.json', 'candidate-pool-after.json',
    'outer-only-policy.json', 'outer_metric.py', 'queries.txt', 'search-map.json',
    'wrapper-run.json', 'wrapper-candidate.json', 'seed-evaluation.json', 'seed-record.json',
    'unpublished-metric-guard.txt', 'common.py', 'prepare_r13.py', 'candidate_r13.py',
    'archive_prepared_r13.py', 'prepare_candidate.sh', 'preparation-recovery.json']
paths = [(ROOT / name, DEST / name) for name in names]
paths += [(ROOT / 'prepare-1797109.out', DEST / 'logs/initial-prepare-1797109.out'),
          (ROOT / 'select-1797061.out', DEST / 'logs/select-1797061.out')]
paths += [(ROOT / 'portable-outer-measurements.json', DEST / 'outer-measurements.json'),
          (ROOT / 'portable-search-evidence.json', DEST / 'r12-search-evidence.json')]
run_dir = SITE / '.autoresearch-wrapper/runs' / run['run_id']
paths += [(run_dir / name, DEST / name) for name in ['program.md', 'results.tsv']]
for source,target in paths:
    assert source.is_file() and not target.exists(), source
    assert not re.search(r'(?i)tvly-[a-z0-9_-]{16,}|authorization:\s*bearer\s+[a-z0-9_-]{16,}|x-api-key\s*:\s*[a-z0-9_-]{16,}', source.read_text()), source.name
for source,target in paths:
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
worktree = Path(change['candidate']['worktree_path'])
assert not git(worktree, 'status', '--porcelain')
replay = subprocess.run([sys.executable, str(DEST / 'outer_metric.py')], cwd=worktree.parent / 'seed',
                         capture_output=True, text=True, check=True)
expected_metric = 100 * context['seed_observation']['project_citations'] / 60
actual_metric = float(next(line.split('=',1)[1] for line in replay.stdout.splitlines() if line.startswith('METRIC=')))
assert abs(actual_metric - expected_metric) < 1e-9
guard = subprocess.run([sys.executable, str(DEST / 'outer_metric.py')], cwd=worktree, capture_output=True, text=True)
assert guard.returncode == 2 and 'No live measurement' in guard.stderr
status = cli('status', '--json', name='wrapper-status.json')
DEST.joinpath('wrapper-status.json').write_text(status)
hashes = {path.relative_to(DEST).as_posix(): digest(path) for path in sorted(DEST.rglob('*')) if path.is_file()}
report = {'passed': True, 'local_checks': len(validation['checks']), 'history_count': 13,
    'proposal_count': 8, 'nonselected_proposals_preserved': 7, 'unmeasured_proposals': 3,
    'candidate_commit': change['candidate_commit'], 'candidate_tree': change['candidate_tree'],
    'seed_metric_replay': replay.stdout.strip(), 'candidate_guard_exit': guard.returncode,
    'outer_status': 'Unmeasured; separate R13 publication approval and complete real outer collection required',
    'sha256': hashes}
DEST.joinpath('audit.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({key:value for key,value in report.items() if key != 'sha256'}, indent=2))
