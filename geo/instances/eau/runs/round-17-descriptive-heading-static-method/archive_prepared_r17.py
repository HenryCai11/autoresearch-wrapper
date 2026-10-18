"""Preserve all old candidates and audit the new unmeasured R17 combination."""
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
assert pool['history'] == before['history'] and len(pool['history']) == 17
assert all(entry['retain_for_combinations'] for entry in pool['history'])
assert pool['best_observed'] == before['best_observed'] and pool['best_observed']['round'] == 16
assert all(proposal in pool['proposals'] for proposal in before['proposals'])
assert len(before['proposals']) == 10 and len(pool['proposals']) == 11
assert {p['id'] for p in pool['proposals']} - {p['id'] for p in before['proposals']} == {SELECTED}
selected = next(p for p in pool['proposals'] if p['id'] == SELECTED)
assert selected['parents'] == ['r16', 'r13']
assert selected['measured'] is False and 'outer_observation' not in selected
assert len([p for p in pool['proposals'] if not p.get('measured', False)]) == 2
assert git(PRODUCTION, 'rev-parse', 'HEAD') == change['current_production_commit']
assert not git(PRODUCTION, 'status', '--porcelain')
registry = json.loads(ROOT.joinpath('outer-measurements.json').read_text())
assert len(registry['measurements']) == 1
registry['measurements'][0]['matrix'] = '../round-16-descriptive-section-headings/r16-live/search-matrix.csv'
write('portable-outer-measurements.json', registry)
evidence = json.loads(ROOT.joinpath('r16-search-evidence.json').read_text())
for item in evidence['observations']:
    item['raw_file'] = '../round-16-descriptive-section-headings/r16-live/gpt-web-answers.jsonl'
    item['raw_files'] = {engine: '../round-16-descriptive-section-headings/r16-live/' + Path(name).name
                         for engine,name in item['raw_files'].items()}
write('portable-search-evidence.json', evidence)
ROOT.joinpath('README.md').write_text(f'''# EAU R17 — descriptive headings with retained static method reference

Status: **validated local candidate; not published or measured**.

- Run: {run['run_id']}; sequential, one index.html candidate.
- New proposal: descriptive-heading-static-method; unmeasured.
- Candidate: {change['candidate_commit']}.
- Tree: {change['candidate_tree']}.
- Seed: best fully measured R16 {change['selection_seed_commit']},
  9/60 citations and composite 31.86111, keep; historical control, not new searches.
- Production remains R16 {change['current_production_commit']}, unchanged.
- Keep threshold is now strictly more than 9/60, not the old R9 8/60 bar.

## A separately identified combination

R17 keeps both R16 descriptive section headings and adds exactly one retained
R13 operation: persistent environment/agent explanations, copied verbatim from
the existing script.js titles, descriptions and six knob labels. The existing
user tab description is not duplicated. The interactive tabs stay unchanged;
the new articles reuse the existing timescales and knob-list styles.
No new method claim, wording, result value, link, script, style or schema is
invented. Existing default result data and the entire results section remain
unchanged. No R12 H1 or R14 second-backbone table is inherited.

combination-source.json records both original commit/tree IDs and copied
operation hashes under parents/. R13's operation independently reproduced its
entire original HTML from R9, and the two R16 operations independently reproduced
the R16 seed from R9. Removing only the new method insertion recovers R16 exactly.
Reversing only the two R16 headings in R17 recovers the original R13 HTML exactly.
The R17 intervention is one operation relative to R16, not reapplication of its
inherited heading operations.

The hypothesis is passage completeness under the clearer method heading.
R16 returned eight explicit homepage URL cells and zero support-page URL cells;
fuzzy queries still had zero domain citations. That is an observed entry surface,
not predicted lift. R13 measured 7/60 against R9 and was discarded; the different
R15 H1/method/table bundle measured 6/60 and was also discarded. Those historical
samples are retained, not added or averaged with R16's 9/60 to predict R17.
An eventual measurement ranks the whole new candidate, not individual modules.

## Cross-module scope and retained history

module-review.json covers all ten inventory modules and retained alternatives.
Only index.html's framework section differs from the current R16 production,
by the exact R13 insertion. Both R16 H2s, the original H1/subtitle, R7 overview,
R8 routes, R9 default result evidence, all other sections/pages, scripts,
styles, metadata and links remain unchanged. Full changes are in candidate.patch
and production-to-candidate.patch.

All 17 R0–R16 observations and ten old proposals are unchanged. An eleventh
proposal records R17 separately. The best_observed record remains R16; an
unmeasured combination never becomes the best by inheritance. Only R17 and the
external-authority proposal are unmeasured. The external paper backlink state is
still unknown and any edit requires separate author authority. This is an
agent-maintained instance ledger, not an automatic recombination scheduler.

## Local validation and publication gate

All {len(validation['checks'])} structural/factual checks passed. Visible homepage:
{validation['visible_home_chars_before']} → {validation['visible_home_chars_after']}
characters, below the unchanged {validation['limit']} limit.
Checks cover exact parent replay/composition, unchanged R16 headings/results,
verbatim JS descriptions and knobs, IDs/links, hidden text, unchanged metadata,
and frozen map/query/judge/normalizer/settings/control-matrix fingerprints.
No inner score was computed. No browser/visual test was performed: existing
markup/styles do not establish rendered fit or interactive behavior.

The exact-tree metric refuses this unpublished combination. Separate explicit
R17 publication approval is required. Starting from then-current main, apply
the exact R16-based candidate and verify its complete tree, reconciling teammate
changes. Verify served bytes before collection and after all real requests finish.

After approval, collect the same frozen 15 queries × GPT web / Codex / Tavily /
Exa, without a memory-model dimension. Require all 60 responses valid and
strictly more than the preserved R16 9/60 citation cells for keep; ties discard.
The unchanged judge also counts bare project-domain occurrences, so explicit
source URLs must be reported separately. R16 is a historical control, not a fresh
simultaneous one. Immediate samples cannot establish causal contribution or
exclude stale indexes. No follow-up is scheduled.

Preparation, baseline replay and validation used Slurm, one CPU and 1 GB.
No site publication/push, new R17 paid searches, rollback, branch pruning or
candidate deletion was performed. The patch, original operations and source
evidence are archived in durable project storage, not only temporary scratch.
''')
names = ['README.md', 'change.json', 'production-context.json', 'validation.json',
    'combination-source.json', 'static-component-source.json', 'new-proposals.json',
    'parents/r13-operations.json', 'parents/r16-operations.json', 'collection-settings.json',
    'operations.json', 'candidate.patch', 'production-to-candidate.patch', 'module-review.json',
    'config.json', 'graph-before.json', 'graph-after.json', 'priorities.json', 'decision.json',
    'exploration.json', 'preview.json', 'applied.json', 'candidate-pool-before.json',
    'candidate-pool-selected.json', 'candidate-pool-after.json', 'outer-only-policy.json',
    'outer_metric.py', 'queries.txt', 'search-map.json', 'wrapper-run.json', 'wrapper-candidate.json',
    'seed-evaluation.json', 'seed-record.json', 'unpublished-metric-guard.txt', 'common.py',
    'prepare_r17.py', 'candidate_r17.py', 'archive_prepared_r17.py', 'prepare_candidate.sh', 'select_candidate.sh', 'r16-production-index.html']
paths = [(ROOT / name, DEST / name) for name in names]
paths += [(ROOT / 'portable-outer-measurements.json', DEST / 'outer-measurements.json'),
          (ROOT / 'portable-search-evidence.json', DEST / 'r16-search-evidence.json')]
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
assert 'LIVE_PROJECT_CITATIONS=9/60' in replay.stdout
guard = subprocess.run([sys.executable, str(DEST / 'outer_metric.py')], cwd=worktree, capture_output=True, text=True)
assert guard.returncode == 2 and 'No live measurement' in guard.stderr
DEST.joinpath('wrapper-status.json').write_text(cli('status', '--json', name='wrapper-status.json'))
hashes = {path.relative_to(DEST).as_posix(): digest(path) for path in sorted(DEST.rglob('*')) if path.is_file()}
audit = {'passed': True, 'local_checks': len(validation['checks']), 'history_count': 17,
    'old_proposals_preserved': 10, 'proposal_count': 11, 'unmeasured_proposals': 2,
    'candidate_commit': change['candidate_commit'], 'candidate_tree': change['candidate_tree'],
    'applied_operations': 1, 'inherited_heading_operations': 2, 'seed_metric_replay': replay.stdout.strip(),
    'candidate_guard_exit': guard.returncode, 'outer_status': 'Unmeasured combination; explicit R17 approval and real complete live collection required',
    'sha256': hashes}
DEST.joinpath('audit.json').write_text(json.dumps(audit, indent=2) + '\n')
print(json.dumps({key:value for key,value in audit.items() if key != 'sha256'}, indent=2))
