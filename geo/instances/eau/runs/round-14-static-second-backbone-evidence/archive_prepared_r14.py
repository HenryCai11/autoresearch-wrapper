"""Archive the unmeasured R14 intervention and prove history/metric guards remain intact."""
import re
import shutil
import sys
from common import *

assert os.environ.get('SLURM_JOB_ID')
change = json.loads(ROOT.joinpath('change.json').read_text())
validation = json.loads(ROOT.joinpath('validation.json').read_text())
run = json.loads(ROOT.joinpath('wrapper-run.json').read_text())
pool = json.loads(INSTANCE.joinpath('candidate-pool.json').read_text())
before = json.loads(ROOT.joinpath('candidate-pool-before.json').read_text())
assert change['state'] == 'validated_awaiting_deployment_approval' and all(validation['checks'].values())
assert not DEST.exists(), 'Append-only archive refuses overwrite'
assert pool['history'] == before['history'] and len(pool['history']) == 14
assert {entry['id'] for entry in pool['history']} == {f'r{i}' for i in range(14)}
assert all(entry['retain_for_combinations'] for entry in pool['history'])
assert all(p in pool['proposals'] for p in before['proposals'] if p['id'] != SELECTED)
selected = next(p for p in pool['proposals'] if p['id'] == SELECTED)
assert selected['original_proposal'] == next(p for p in before['proposals'] if p['id'] == SELECTED)
assert len(pool['proposals']) == len(before['proposals']) == 8
assert not selected['measured'] and 'outer_observation' not in selected
assert len([p for p in pool['proposals'] if not p.get('measured', False)]) == 2
assert git(PRODUCTION, 'rev-parse', 'HEAD') == change['current_production_commit']
assert git(PRODUCTION, 'rev-parse', 'HEAD^{tree}') == change['current_production_tree']
assert not git(PRODUCTION, 'status', '--porcelain')
registry = json.loads(ROOT.joinpath('outer-measurements.json').read_text())
assert len(registry['measurements']) == 1
assert registry['measurements'][0]['deployed_tree'] == change['selection_seed_tree']
registry['measurements'][0]['matrix'] = '../round-9-static-benchmark-evidence/r9-live/search-matrix.csv'
write('portable-outer-measurements.json', registry)
evidence = json.loads(ROOT.joinpath('r13-search-evidence.json').read_text())
for item in evidence['observations']:
    item['raw_file'] = '../round-13-static-component-reference/r13-live/gpt-web-answers.jsonl'
    item['raw_files'] = {engine: '../round-13-static-component-reference/r13-live/' + Path(name).name
                         for engine,name in item['raw_files'].items()}
write('portable-search-evidence.json', evidence)
ROOT.joinpath('README.md').write_text(f'''# EAU R14 — static second-backbone evidence

Status: **validated local candidate; not published or measured**.

- Wrapper run: {run['run_id']}; sequential, one candidate, index.html target.
- Existing pool proposal: static-second-backbone-evidence.
- Candidate commit: {change['candidate_commit']}.
- Candidate tree: {change['candidate_tree']}.
- Selection seed: R9 {change['selection_seed_commit']}, best preserved complete
  outer measurement: 8/60 citations, composite 30.25.
- Current production remains R13 {change['current_production_commit']},
  7/60 citations, composite 30.14, discard. It is not the keep threshold.
- No new R14 search response or inner score exists.

## One coherent change

Add a separately captioned Qwen2.5-7B-Instruct reference table in the existing
results section. It is a default-open semantic details/table block, so its
content does not require JavaScript or a model-switch click. Its nine method
rows and 36 values are copied from the existing results.qwen25 object in
script.js, preserving three-decimal precision, column order and model label.
No new results, relative gains, tau2 numbers or research claims are introduced.

The existing Qwen3 charts/table, switch buttons, default selection, original
noscript fallback and all other homepage bytes remain. The existing fallback
still describes the main default Qwen3 display; the new reference is separately
captioned. The new table uses unique IDs that are not renderer targets; the
switch above continues to control the main charts and main comparison table.
All scripts, styles, metadata, links and other pages are unchanged. Existing
table-scroll and result-table-details styling is reused.

The latest R13 measurement returned four explicit homepage URL cells and no
support-page URLs. This locates an observed entry surface, not a prediction
that another table will improve rankings. R9's kept static default results
provide a reusable implementation parent; its old score is not added to
anything to predict this candidate's score.

## Cross-module and retained-candidate review

module-review.json reviews all ten inventory modules, including reference-page
routing and the author-owned external paper entry. All 14 R0–R13 history entries
and all eight proposals remain. Seven non-selected proposal entries are
unchanged; the original queued proposal is retained inside the selected entry.
The external backlink remains unknown and any edit needs separate authority.

R10 scholarly metadata, R11 overview restoration, R12 H1 and R13 static component
description candidates remain available for later combinations but are not
silently inherited. R14 starts from the best observed R9 tree, retaining its R7
overview, R8 reference routes and R9 default static results. Relative to current
R13 production, index.html both adds this table and removes R13's unkept static
component block. That full difference is in production-to-candidate.patch.

## Validation and outer gate

All {len(validation['checks'])} local checks passed. Homepage visible text:
{validation['visible_home_chars_before']} → {validation['visible_home_chars_after']}
characters, below the unchanged {validation['limit']} limit. Independent HTML
parsing verifies all nine table rows and 36 values against the existing JS, and
separately verifies the default Qwen3 rows. Exact insertion scope, labels, IDs,
links, no hidden text, unchanged schema/scripts/styles and frozen
map/query/judge/normalizer hashes were checked. No inner score was computed.

No browser or visual test was performed. Preserved markup/selectors and reused
styles are structural checks, not proof of rendered behavior or layout.

The exact-tree metric guard refuses to score this unpublished candidate.
Separate explicit R14 publication approval is required. After approval, apply
the exact candidate index.html in an isolated deploy branch based on current
main and verify the entire tree. A blind merge into R13 would retain the wrong
component block. Reconcile concurrent teammate changes before proceeding.
Verify served bytes before collection and after all requests have completed.

Use the same 15 queries × GPT web / Codex / Tavily / Exa settings, with no memory
model dimension. Require 60 valid cells and strictly more than R9's 8/60
project-domain citation cells for keep; ties discard. The judge counts bare
domain occurrences, so explicit URLs must be reported separately. The control
is historical, not freshly collected or simultaneous. One immediate sample
cannot establish causality or exclude stale search indexes.

Preparation and metric replay used Slurm with one CPU and 1 GB. No site push,
publication, rollback, branch pruning, candidate deletion, R14 paid searches or
future follow-up was performed. The patch, source data and history live in this
durable instance archive, not only in temporary scratch worktrees.
''')
names = ['README.md', 'change.json', 'production-context.json', 'validation.json',
    'static-second-backbone-source.json', 'operations.json', 'candidate.patch', 'production-to-candidate.patch',
    'module-review.json', 'config.json', 'graph-before.json', 'graph-after.json', 'priorities.json',
    'decision.json', 'exploration.json', 'preview.json', 'applied.json',
    'candidate-pool-before.json', 'candidate-pool-selected.json', 'candidate-pool-after.json',
    'outer-only-policy.json', 'outer_metric.py', 'queries.txt', 'search-map.json',
    'wrapper-run.json', 'wrapper-candidate.json', 'seed-evaluation.json', 'seed-record.json',
    'unpublished-metric-guard.txt', 'common.py', 'prepare_r14.py', 'candidate_r14.py',
    'archive_prepared_r14.py', 'prepare_candidate.sh', 'r13-production-index.html']
paths = [(ROOT / name, DEST / name) for name in names]
paths += [(ROOT / 'portable-outer-measurements.json', DEST / 'outer-measurements.json'),
          (ROOT / 'portable-search-evidence.json', DEST / 'r13-search-evidence.json')]
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
assert 'LIVE_PROJECT_CITATIONS=8/60' in replay.stdout
guard = subprocess.run([sys.executable, str(DEST / 'outer_metric.py')], cwd=worktree, capture_output=True, text=True)
assert guard.returncode == 2 and 'No live measurement' in guard.stderr
status = cli('status', '--json', name='wrapper-status.json')
DEST.joinpath('wrapper-status.json').write_text(status)
hashes = {path.relative_to(DEST).as_posix(): digest(path) for path in sorted(DEST.rglob('*')) if path.is_file()}
report = {'passed': True, 'local_checks': len(validation['checks']), 'history_count': 14,
    'proposal_count': 8, 'nonselected_proposals_preserved': 7, 'unmeasured_proposals': 2,
    'source_rows': 9, 'source_numeric_values': 36,
    'candidate_commit': change['candidate_commit'], 'candidate_tree': change['candidate_tree'],
    'seed_metric_replay': replay.stdout.strip(), 'candidate_guard_exit': guard.returncode,
    'outer_status': 'Unmeasured; separate R14 approval and exact-tree deployment plus complete real 60-cell collection required',
    'sha256': hashes}
DEST.joinpath('audit.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({key:value for key,value in report.items() if key != 'sha256'}, indent=2))
