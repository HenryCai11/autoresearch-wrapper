"""Preserve all old candidates and audit the new unmeasured R16 heading candidate."""
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
assert pool['history'] == before['history'] and len(pool['history']) == 16
assert all(entry['retain_for_combinations'] for entry in pool['history'])
assert all(proposal in pool['proposals'] for proposal in before['proposals'])
assert len(before['proposals']) == 9 and len(pool['proposals']) == 10
assert {p['id'] for p in pool['proposals']} - {p['id'] for p in before['proposals']} == {SELECTED}
selected = next(p for p in pool['proposals'] if p['id'] == SELECTED)
assert selected['parents'] == ['r9']
assert selected['measured'] is False and 'outer_observation' not in selected
assert len([p for p in pool['proposals'] if not p.get('measured', False)]) == 2
assert git(PRODUCTION, 'rev-parse', 'HEAD') == change['current_production_commit']
assert not git(PRODUCTION, 'status', '--porcelain')
registry = json.loads(ROOT.joinpath('outer-measurements.json').read_text())
assert len(registry['measurements']) == 1
registry['measurements'][0]['matrix'] = '../round-9-static-benchmark-evidence/r9-live/search-matrix.csv'
write('portable-outer-measurements.json', registry)
evidence = json.loads(ROOT.joinpath('r15-search-evidence.json').read_text())
for item in evidence['observations']:
    item['raw_file'] = '../round-15-static-entry-combination/r15-live/gpt-web-answers.jsonl'
    item['raw_files'] = {engine: '../round-15-static-entry-combination/r15-live/' + Path(name).name
                         for engine,name in item['raw_files'].items()}
write('portable-search-evidence.json', evidence)
ROOT.joinpath('README.md').write_text(f'''# EAU R16 — descriptive section headings

Status: **validated local candidate; not published or measured**.

- Run: {run['run_id']}; sequential, one index.html candidate.
- New pool proposal: descriptive-section-headings; unmeasured.
- Candidate: {change['candidate_commit']}.
- Tree: {change['candidate_tree']}.
- Seed: best fully measured R9 {change['selection_seed_commit']},
  8/60 citations and composite 30.25; historical, not newly collected.
- Production remains R15 {change['current_production_commit']},
  6/60 citations and composite 29.75, discard; not the selection threshold.

## One small intervention

Replace exactly two existing visible H2 labels on R9:

| Section | Before | After |
| --- | --- | --- |
| Framework | A feedback loop. / With room to change. | How EAU adapts / the training system. |
| Results | Better interactions. / Stronger agents. | EAU results on / UserGym and ColBench. |

Both IDs, their aria-labelledby references, and br/em structure are preserved.
The terms are supported by the unchanged knowledge map and existing visible
project passages, recorded in heading-source.json. No new factual claim,
number, link, metadata, result row, body paragraph or keyword block is added.
The results heading highlights the existing main tables; the tau2 subsection
and its evidence boundary remain unchanged.

The hypothesis is clearer method/benchmark context for passages on the
homepage. R15 had 6/60 domain-citation cells, all in exact queries, zero in
fuzzy/broad queries, and four explicit homepage URL cells with zero support-page
URL cells. That locates an observed entry surface; it does not predict heading
lift. R16 has no outer score. Immediate historical samples cannot isolate causal
module effects or exclude stale indexes.

## Scope and retained history

Only index.html differs from R9, by two heading replacements. The original R9
H1 and subtitle, R7 overview, R8 routes, R9 static default results, all other
sections, pages, scripts, styles, links and metadata remain unchanged.
Relative to current R15 production, the candidate also removes R15's unkept H1,
static component reference and second-backbone table. This full difference is
in production-to-candidate.patch; do not blindly merge the R9-based branch into
R15 and accidentally retain those deltas.

All 16 R0–R15 history entries and all nine old proposals remain unchanged. A
tenth proposal records this new heading test. Both it and the external-authority
proposal remain unmeasured. R12/R13/R14/R15 operations and observations are
retained for later combinations; their scores are not added to predict R16.
module-review.json covers all ten inventory modules and retained alternatives.
The external paper backlink state is still unknown, and any edit requires
separate author authority. This ledger is agent-maintained instance data, not an
automatic wrapper-core recombination scheduler.

## Validation and publication gate

All {len(validation['checks'])} structural/factual checks passed. Visible homepage:
{validation['visible_home_chars_before']} → {validation['visible_home_chars_after']}
characters, below the unchanged {validation['limit']} limit. Reversing the two
operations recovers the complete R9 HTML exactly. IDs, links, reference order,
source facts, default table bytes, unchanged JSON-LD/scripts/styles and frozen
map/query/judge/normalizer hashes are independently checked.
No inner score was computed. No browser/visual test was performed: preserving
markup and styles does not establish rendered heading wrapping or layout.

The exact-tree metric guard rejects this unpublished candidate. Separate
explicit R16 publication approval is required. Use an isolated deploy branch
based on then-current main, apply the exact candidate index.html, verify its
complete tree, and reconcile teammate changes. Verify served bytes before
collection and after all real requests complete.

After approval, use the same 15 queries × GPT web / Codex / Tavily / Exa,
without a memory-model dimension. Require 60 valid cells and strictly more than
R9's 8/60 citation cells for keep; ties discard. The frozen judge counts bare
project-domain occurrences, so explicit source URLs must be reported separately.
The R9 control is historical, not simultaneous. No follow-up is scheduled.

Preparation and replay used Slurm, one CPU and 1 GB. No site publication/push,
rollback, new R16 paid searches, candidate deletion or branch pruning was
performed. Source evidence and the candidate patch are archived in durable
project storage, not only temporary scratch.
''')
names = ['README.md', 'change.json', 'production-context.json', 'validation.json',
    'heading-source.json', 'heading-source-checks.json', 'new-proposals.json',
    'operations.json', 'candidate.patch', 'production-to-candidate.patch', 'module-review.json',
    'config.json', 'graph-before.json', 'graph-after.json', 'priorities.json', 'decision.json',
    'exploration.json', 'preview.json', 'applied.json', 'candidate-pool-before.json',
    'candidate-pool-selected.json', 'candidate-pool-after.json', 'outer-only-policy.json',
    'outer_metric.py', 'queries.txt', 'search-map.json', 'wrapper-run.json', 'wrapper-candidate.json',
    'seed-evaluation.json', 'seed-record.json', 'unpublished-metric-guard.txt', 'common.py',
    'prepare_r16.py', 'candidate_r16.py', 'archive_prepared_r16.py', 'prepare_candidate.sh', 'select_candidate.sh', 'r15-production-index.html',
    'resume_prepared_r16.py', 'resume_candidate.sh', 'preparation-recovery.json']
paths = [(ROOT / name, DEST / name) for name in names]
paths += [(ROOT / 'portable-outer-measurements.json', DEST / 'outer-measurements.json'),
          (ROOT / 'portable-search-evidence.json', DEST / 'r15-search-evidence.json')]
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
audit = {'passed': True, 'local_checks': len(validation['checks']), 'history_count': 16,
    'old_proposals_preserved': 9, 'proposal_count': 10, 'unmeasured_proposals': 2,
    'candidate_commit': change['candidate_commit'], 'candidate_tree': change['candidate_tree'],
    'heading_operations': 2, 'seed_metric_replay': replay.stdout.strip(),
    'candidate_guard_exit': guard.returncode, 'outer_status': 'Unmeasured heading candidate; explicit R16 approval and real complete live collection required',
    'sha256': hashes}
DEST.joinpath('audit.json').write_text(json.dumps(audit, indent=2) + '\n')
print(json.dumps({key:value for key,value in audit.items() if key != 'sha256'}, indent=2))
