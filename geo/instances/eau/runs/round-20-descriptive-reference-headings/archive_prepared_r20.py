"""Append-only, portable R20 archive; no publication or new external evaluation."""
import re
import shutil
import sys
from common import *

assert os.environ.get('SLURM_JOB_ID')
assert not DEST.exists(), 'Append-only archive refuses overwrite'
change = json.loads(ROOT.joinpath('change.json').read_text())
validation = json.loads(ROOT.joinpath('validation.json').read_text())
run = json.loads(ROOT.joinpath('wrapper-run.json').read_text())
pool = json.loads(INSTANCE.joinpath('candidate-pool.json').read_text())
before = json.loads(ROOT.joinpath('candidate-pool-before.json').read_text())
assert change['state'] == 'validated_awaiting_deployment_approval' and all(validation['checks'].values())
assert pool['history'] == before['history'] and len(pool['history']) == 20
assert all(h['retain_for_combinations'] for h in pool['history'])
assert pool['best_observed'] == before['best_observed'] and pool['best_observed']['round'] == 18
assert len(pool['proposals']) == 14 and len(before['proposals']) == 13
assert all(p in pool['proposals'] for p in before['proposals'])
selected = next(p for p in pool['proposals'] if p['id'] == SELECTED)
assert selected['parents'] == ['r18'] and selected['measured'] is False and 'outer_observation' not in selected
assert {p['id'] for p in pool['proposals'] if not p.get('measured',False)} == {SELECTED,'external-paper-link-audit'}
assert git(PRODUCTION,'rev-parse','HEAD') == change['current_production_commit'] and not git(PRODUCTION,'status','--porcelain')
registry = json.loads(ROOT.joinpath('outer-measurements.json').read_text())
assert len(registry['measurements']) == 1 and registry['measurements'][0]['label'] == 'r18-best-reused-control'
registry['measurements'][0]['matrix'] = '../round-18-alphaxiv-paper-routing/r18-live/search-matrix.csv'
write('portable-outer-measurements.json',registry)
evidence = json.loads(ROOT.joinpath('r19-search-evidence.json').read_text())
for item in evidence['observations']:
    item['raw_file'] = '../round-19-shared-entity-combination/r19-live/gpt-web-answers.jsonl'
    item['raw_files'] = {engine:'../round-19-shared-entity-combination/r19-live/' + Path(name).name for engine,name in item['raw_files'].items()}
    assert all((DEST / name).resolve().is_file() for name in item['raw_files'].values())
write('portable-search-evidence.json',evidence)
jobs = ['1846207','1846228','1846271','1846284']
accounting = subprocess.check_output(['sacct','--jobs',','.join(jobs),'--noheader','--parsable2','--format=JobIDRaw,JobName,State,ExitCode'],text=True)
write('slurm-provenance.json',{'selection_job':'1846207','seed_and_allocation_job':'1846228',
    'first_validation_job':'1846271','corrected_validation_job':'1846284','archive_job':os.environ['SLURM_JOB_ID'],
    'resources':'Each Python/CLI job: CPU only, account aip-xiye17, 1 CPU, 1 GB, 5 minutes; all job I/O in scratch',
    'accounting_before_archive_completion':accounting,
    'correction':'First validation stopped on KeyError index.html before writing validation or committing. Corrected URL keys to / and /<file>.html; no site change, paid search, metric or candidate record was produced by that failed attempt.'})
ROOT.joinpath('README.md').write_text(f'''# EAU R20 — descriptive reference-page H1s

Status: **validated local candidate; not published or measured**.

- Run: {run['run_id']}; sequential, one two-heading candidate.
- Candidate: {change['candidate_commit']}.
- Tree: {change['candidate_tree']}.
- Selection seed: best complete measured R18 {change['selection_seed_commit']}.
- Historical control: original R18 12/60 citations, primary 20.00/100;
  secondary composite 35.19444. This is not a fresh simultaneous control.
- Production remains unchanged R19 {change['current_production_commit']}.
- Keep requires all 60 valid and strictly more than 12/60; ties discard.

## Cross-module selection and wording provenance

The latest complete R19 observation tied R18 in the same twelve citation cells.
Its source URLs still include method.html in one fuzzy Exa cell and
research-context.html in another. Paper.html appears in three exact-query cells.
These actual returned source URLs motivate a visible-heading test, not a claim
that the earlier schema bundle or these headings caused retrieval. See
observed-entry-surfaces.json and r19-search-evidence.json, which points to the
unchanged archived R19 raw answers. No new R20 searches were made.

R20 changes exactly two H1 elements relative to R18:

| Page | Before | After |
| --- | --- | --- |
| method.html | What does EAU adapt? | How EAU adapts the training system. |
| research-context.html | Where does EAU fit? | EAU as an adaptive training system. |

The method wording exactly reuses R16's existing framework H2 still present on
the R18 homepage; the context wording uses its existing lead description.
This is a new support-page H1 bundle, not replay of the R16 homepage operation,
and no R16 score is inherited. Parent is R18 only. There are no new scientific,
performance, author, affiliation, benchmark or identity claims.

All paragraphs, secondary headings, evidence tables and citation/PDF/BibTeX
fields remain byte-identical to R18. All four HTML heads and JSON-LD blocks,
the complete homepage/paper page, scripts, styles, assets, crawler files,
README, llms.txt and site-config.js are unchanged versus R18. All nine R18
alphaXiv routing operations, including six HTML reading anchors, are retained.
Scholarly arXiv references are unchanged. Neither external domain counts as a
project citation; alphaXiv traffic remains unmeasured.

module-review.json reviews all ten modules and thirteen older proposals. All
twenty R0–R19 observations, all thirteen older proposals and best_observed R18
remain unchanged. Fourteen proposals now exist; only R20 and the external-paper
authority proposal are unmeasured. Discarded candidates remain available for
future combinations. Parent scores are never summed or used as isolated effects.
This is an agent-maintained ledger, not a background scheduler.

## Seed scope versus production scope

R19 remains live, but its tied schema experiment was discarded for selection.
It is NOT the R20 seed, and its distinct matrix is NOT relabelled as the R18
control. Candidate.patch contains only the two H1 replacements relative to R18.
production-to-candidate.patch spans FOUR HTML files: restore the R18 metadata
in index/method/paper/context, then change the two reference H1s. The unchanged
production snapshot is under served-r19/. Reversing the two new H1s and
reapplying the four exact archived R19 JSON-LD operations reproduces current
production byte-for-byte. This deployment scope is explicit, not a claim that
only two files differ from the currently live site. No rollback is performed now.

## Validation and publication gate

All {len(validation['checks'])} structural/factual checks passed, including
exact two-replacement replay/reversal, four-file production reconstruction,
existing wording provenance, alphaXiv routing, JSON-LD parsing, local paths,
fragments, unique IDs, hidden text and frozen matrix/query/map/judge/normalizer/
engine settings. The homepage remains {validation['visible_home_chars_after']}
visible characters under the unchanged {validation['limit']} limit. Reference
page text lengths before/after are recorded in validation.json.

Both edited files are content-fingerprinted linked asset graph nodes with empty
operation lists. Main-agent apply_patch made the exact two replacements in the
allocated worktree; no geo-apply support or wrapper-core extension is claimed.
The before/after graph snapshots and edit-mechanism.json preserve that limitation.
No inner score was computed and no browser/visual test was performed; heading
wrapping and layout are not described as tested.

Python, wrapper CLI, seed replay and validation ran through CPU Slurm jobs.
The first validation stopped on a URL-key error before validation output or
commit; it was corrected without site publication, resampling or metric changes.
See slurm-provenance.json and logs/ for the failed and successful attempts.

The portable exact-tree metric replays only the original registered R18 result
and rejects this unmeasured R20 tree with exit 2. No candidate metric, crash
record or fabricated 60-cell result is registered. Explicit publication approval
is required next. Recheck then-current main for teammate changes, verify the
complete candidate tree and all FOUR changed served HTML files before and after
the frozen 15-query × GPT web / Codex / Tavily / Exa collection. The unchanged
settings file retains legacy R9 wording; actual registered control is R18.
There is no memory dimension. Bare project-domain citation cells and explicit
source URLs remain separate. Immediate historical-control measurements cannot
establish causal module contributions or exclude stale indexing.

No site publication/push, new paid searches, rollback, pruning, deletion,
automatic follow-up or next-round start was performed.
''')
names = ['README.md','change.json','production-context.json','validation.json','wording-source.json',
    'observed-entry-surfaces.json','new-proposals.json','collection-settings.json','operations.json','manual-operations.json',
    'candidate.patch','production-to-candidate.patch','module-review.json','config.json','graph-before.json','graph-after.json',
    'priorities.json','decision.json','exploration.json','edit-mechanism.json','candidate-pool-before.json',
    'candidate-pool-selected.json','candidate-pool-after.json','outer-only-policy.json','outer_metric.py','queries.txt',
    'search-map.json','wrapper-run.json','wrapper-candidate.json','seed-evaluation.json','seed-record.json',
    'unpublished-metric-guard.txt','common.py','prepare_r20.py','allocate_r20.py','candidate_r20.py',
    'archive_prepared_r20.py','select_candidate.sh','allocate_candidate.sh','prepare_candidate.sh','archive_candidate.sh',
    'slurm-provenance.json','wrapper-scan.txt','wrapper-configure.txt']
names += ['sources/' + p.name for p in sorted(ROOT.joinpath('sources').iterdir())]
names += ['control/' + name for name in ['summary.json','search-matrix.csv','search-map.json']]
names += ['served-r19/' + name for name in HTML]
paths = [(ROOT / name,DEST / name) for name in names]
paths += [(ROOT / 'portable-outer-measurements.json',DEST / 'outer-measurements.json'),
    (ROOT / 'portable-search-evidence.json',DEST / 'r19-search-evidence.json')]
paths += [(p,DEST / 'logs' / p.name) for p in sorted(ROOT.glob('*.err'))]
paths += [(p,DEST / 'logs' / p.name) for p in sorted(ROOT.glob('validate-*.out'))]
run_dir = SITE / '.autoresearch-wrapper/runs' / run['run_id']
paths += [(run_dir / name,DEST / name) for name in ['program.md','results.tsv']]
worktree = Path(change['candidate']['worktree_path'])
paths += [(worktree / name,DEST / 'site' / name) for name in HTML]
for src,target in paths:
    assert src.is_file() and not target.exists(),src
    assert not re.search(r'(?i)tvly-[a-z0-9_-]{16,}|authorization:\s*bearer\s+[a-z0-9_-]{16,}|x-api-key\s*:\s*[a-z0-9_-]{16,}',src.read_text()),src.name
for src,target in paths:
    target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(src,target)
assert not git(worktree,'status','--porcelain')
seed = subprocess.run([sys.executable,str(DEST / 'outer_metric.py')],cwd=worktree.parent / 'seed',check=True,capture_output=True,text=True)
assert 'LIVE_PROJECT_CITATIONS=12/60' in seed.stdout and 'METRIC=20.0' in seed.stdout
guard = subprocess.run([sys.executable,str(DEST / 'outer_metric.py')],cwd=worktree,capture_output=True,text=True)
assert guard.returncode == 2 and 'No live measurement' in guard.stderr
DEST.joinpath('wrapper-status.json').write_text(cli('status','--json',name='wrapper-status.json'))
hashes = {p.relative_to(DEST).as_posix():digest(p) for p in sorted(DEST.rglob('*')) if p.is_file()}
audit = {'passed':True,'local_checks':len(validation['checks']),'history_count':20,'old_proposals_preserved':13,
    'proposal_count':14,'unmeasured_proposals':2,'candidate_commit':change['candidate_commit'],'candidate_tree':change['candidate_tree'],
    'manual_heading_operations':2,'wrapper_text_operations':0,'changed_files_vs_r18':FILES,'changed_files_vs_live_r19':HTML,
    'seed_metric_replay':seed.stdout.strip(),'candidate_guard_exit':guard.returncode,'archive_job':os.environ['SLURM_JOB_ID'],
    'outer_status':'Unmeasured R20; explicit approval, exact deployment and complete real live collection required','sha256':hashes}
DEST.joinpath('audit.json').write_text(json.dumps(audit,indent=2) + '\n')
print(json.dumps({k:v for k,v in audit.items() if k != 'sha256'},indent=2))
