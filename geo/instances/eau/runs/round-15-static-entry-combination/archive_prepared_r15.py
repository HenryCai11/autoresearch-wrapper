"""Preserve all old candidates and audit the new unmeasured R15 combination."""
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
assert pool['history'] == before['history'] and len(pool['history']) == 15
assert all(entry['retain_for_combinations'] for entry in pool['history'])
assert all(proposal in pool['proposals'] for proposal in before['proposals'])
assert len(before['proposals']) == 8 and len(pool['proposals']) == 9
assert {p['id'] for p in pool['proposals']} - {p['id'] for p in before['proposals']} == {SELECTED}
selected = next(p for p in pool['proposals'] if p['id'] == SELECTED)
assert selected['parents'] == ['r9', 'r12', 'r13', 'r14']
assert selected['measured'] is False and 'outer_observation' not in selected
assert len([p for p in pool['proposals'] if not p.get('measured', False)]) == 2
assert git(PRODUCTION, 'rev-parse', 'HEAD') == change['current_production_commit']
assert not git(PRODUCTION, 'status', '--porcelain')
registry = json.loads(ROOT.joinpath('outer-measurements.json').read_text())
assert len(registry['measurements']) == 1
registry['measurements'][0]['matrix'] = '../round-9-static-benchmark-evidence/r9-live/search-matrix.csv'
write('portable-outer-measurements.json', registry)
evidence = json.loads(ROOT.joinpath('r14-search-evidence.json').read_text())
for item in evidence['observations']:
    item['raw_file'] = '../round-14-static-second-backbone-evidence/r14-live/gpt-web-answers.jsonl'
    item['raw_files'] = {engine: '../round-14-static-second-backbone-evidence/r14-live/' + Path(name).name
                         for engine,name in item['raw_files'].items()}
write('portable-search-evidence.json', evidence)
ROOT.joinpath('README.md').write_text(f'''# EAU R15 — retained static-entry combination

Status: **validated local candidate; not published or measured**.

- Run: {run['run_id']}; sequential, one index.html candidate.
- New pool proposal: static-entry-combination, explicitly unmeasured.
- Candidate: {change['candidate_commit']}.
- Tree: {change['candidate_tree']}.
- Seed: best complete historical R9 {change['selection_seed_commit']},
  8/60 citations and composite 30.25; not newly collected or simultaneous.
- Production remains R14 {change['current_production_commit']},
  5/60 citations and composite 28.89, discard; not the selection threshold.

## What is being combined

R15 replays exactly three retained archived operations on R9:

| Historical candidate | Exact reused intervention |
| --- | --- |
| R12 | Existing EAU/co-evolution identity in the visible H1 |
| R13 | Static environment/agent descriptions and knob labels |
| R14 | Separately captioned, default-open Qwen2.5 result reference |

Each individual operation first reproduced its original parent's entire HTML
byte-for-byte from R9. Their original commit/tree IDs and operation hashes are
in combination-source.json, with copies under parents/. No content is newly
paraphrased or invented. This is an intentional new bundle, not a silent
inheritance of unkept deltas or an edit to the old candidates.

R12, R13 and R14 observed 6/60, 7/60 and 5/60 respectively and were discarded
against R9. Those are historical single samples of entire candidates, not
isolated component effects. They are not added, averaged or otherwise used to
predict the combination. R15 has no outer score. An eventual result would rank
this bundle only, not prove which component caused a gain or loss.

The hypothesis is initial-HTML completeness: existing identity, method
descriptions and evidence might interact differently when present together.
R14 returned three explicit homepage URL cells and no support-page URL cells;
that is source evidence, not a forecast of this bundle's lift.

## Scope and retained history

Only index.html differs from R9. The H1 exactly matches R12, the framework
section exactly matches R13, and the results section exactly matches R14.
Everything else remains on R9, including R7 overview, R8 reference routes,
metadata, all other pages, scripts and styles. Existing default result rows and
switch targets remain; the second-backbone table is not a renderer target.

Relative to current R14 production, its entire results section stays unchanged;
the H1 and component descriptions are the production delta. The full diff is
production-to-candidate.patch. No new facts, model values, metrics, gains,
affiliations or external links are introduced.

All 15 R0–R14 history entries and all eight old proposals are unchanged. A ninth
proposal records this combination separately. Both this proposal and the
external-authority proposal remain unmeasured. The external paper backlink state
is unknown; any edit requires separate author authority. module-review.json
covers all ten inventory modules. This ledger is agent-maintained instance data,
not an automatic global recombination scheduler in wrapper core.

## Validation and publication gate

All {len(validation['checks'])} structural/factual checks passed. Visible homepage:
{validation['visible_home_chars_before']} → {validation['visible_home_chars_after']}
characters, below the existing {validation['limit']} limit. Checks independently
validate component text and six knobs against JS, both nine-row result tables
against JS, exact parent fragments, all IDs/links, no hidden text, unchanged
schema/scripts/styles and frozen map/query/judge/normalizer hashes.
No inner score was computed. No browser/visual test was performed; rendered
layout and runtime behavior are not claimed as browser-tested.

The exact-tree metric guard rejects this unpublished combination. Separate
explicit R15 publication approval is required. Use an isolated deploy branch
based on current main, apply exact candidate index.html, verify the whole tree,
and reconcile any teammate changes. Verify served bytes before collection and
after all requests finish. Never score an unpublished tree as if it were live.

After approval, use the frozen 15 queries × GPT web / Codex / Tavily / Exa,
without a memory-model dimension. Require 60 valid cells and strictly more than
8/60 project-domain citation cells for keep; ties discard. The frozen judge also
counts bare-domain occurrences, so explicit URLs must be reported separately.
Historical controls and immediate samples cannot establish causality or exclude
indexing lag; no follow-up is scheduled automatically.

Preparation and replay used Slurm, one CPU and 1 GB. No site publication/push,
rollback, paid R15 searches, candidate deletion or branch pruning was performed.
The patch, parent operations and evidence are archived in durable project
storage, not only in temporary scratch worktrees.
''')
names = ['README.md', 'change.json', 'production-context.json', 'validation.json',
    'combination-source.json', 'combined-source-checks.json', 'new-proposals.json',
    'parents/r12-operations.json', 'parents/r13-operations.json', 'parents/r14-operations.json',
    'operations.json', 'candidate.patch', 'production-to-candidate.patch', 'module-review.json',
    'config.json', 'graph-before.json', 'graph-after.json', 'priorities.json', 'decision.json',
    'exploration.json', 'preview.json', 'applied.json', 'candidate-pool-before.json',
    'candidate-pool-selected.json', 'candidate-pool-after.json', 'outer-only-policy.json',
    'outer_metric.py', 'queries.txt', 'search-map.json', 'wrapper-run.json', 'wrapper-candidate.json',
    'seed-evaluation.json', 'seed-record.json', 'unpublished-metric-guard.txt', 'common.py',
    'prepare_r15.py', 'candidate_r15.py', 'archive_prepared_r15.py', 'prepare_candidate.sh', 'r14-production-index.html']
paths = [(ROOT / name, DEST / name) for name in names]
paths += [(ROOT / 'portable-outer-measurements.json', DEST / 'outer-measurements.json'),
          (ROOT / 'portable-search-evidence.json', DEST / 'r14-search-evidence.json')]
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
                         check=True, capture_output=True, text=True)
assert 'LIVE_PROJECT_CITATIONS=8/60' in replay.stdout
guard = subprocess.run([sys.executable, str(DEST / 'outer_metric.py')], cwd=worktree, capture_output=True, text=True)
assert guard.returncode == 2 and 'No live measurement' in guard.stderr
DEST.joinpath('wrapper-status.json').write_text(cli('status', '--json', name='wrapper-status.json'))
hashes = {path.relative_to(DEST).as_posix(): digest(path) for path in sorted(DEST.rglob('*')) if path.is_file()}
audit = {'passed': True, 'local_checks': len(validation['checks']), 'history_count': 15,
    'old_proposals_preserved': 8, 'proposal_count': 9, 'unmeasured_proposals': 2,
    'candidate_commit': change['candidate_commit'], 'candidate_tree': change['candidate_tree'],
    'exact_parent_operations': 3, 'seed_metric_replay': replay.stdout.strip(),
    'candidate_guard_exit': guard.returncode, 'outer_status': 'Unmeasured combination; explicit R15 approval and real complete live collection required',
    'sha256': hashes}
DEST.joinpath('audit.json').write_text(json.dumps(audit, indent=2) + '\n')
print(json.dumps({key:value for key,value in audit.items() if key != 'sha256'}, indent=2))
