"""Durable append-only archive for one unmeasured R18/R14 combination."""
import re
import shutil
import sys
from common import *

assert os.environ.get('SLURM_JOB_ID')
assert not DEST.exists(), 'Refuse to overwrite a prepared round'
change = json.loads(ROOT.joinpath('change.json').read_text())
validation = json.loads(ROOT.joinpath('validation.json').read_text())
run = json.loads(ROOT.joinpath('wrapper-run.json').read_text())
pool = json.loads(INSTANCE.joinpath('candidate-pool.json').read_text())
original = json.loads(ROOT.joinpath('candidate-pool-before.json').read_text())
assert change['state'] == 'validated_awaiting_deployment_approval' and all(validation['checks'].values())
assert pool['history'] == original['history'] and len(pool['history']) == 21
assert all(h['retain_for_combinations'] for h in pool['history'])
assert len(pool['proposals']) == 15 and len(original['proposals']) == 14 and all(p in pool['proposals'] for p in original['proposals'])
assert pool['best_observed'] == original['best_observed'] and pool['best_observed']['round'] == 18
chosen = next(p for p in pool['proposals'] if p['id'] == SELECTED)
assert chosen['parents'] == ['r18','r14'] and chosen['measured'] is False and 'outer_observation' not in chosen
assert {p['id'] for p in pool['proposals'] if not p.get('measured',False)} == {SELECTED,'external-paper-link-audit'}
assert next(p for p in pool['proposals'] if p['id'] == 'static-second-backbone-evidence')['status'] == 'discard'
assert git(PRODUCTION,'rev-parse','HEAD') == change['current_production_commit'] and not git(PRODUCTION,'status','--porcelain')
registry = json.loads(ROOT.joinpath('outer-measurements.json').read_text())
assert len(registry['measurements']) == 1 and registry['measurements'][0]['label'] == 'r18-best-reused-control'
registry['measurements'][0]['matrix'] = '../round-18-alphaxiv-paper-routing/r18-live/search-matrix.csv'
write('portable-outer-measurements.json',registry)
previous = INSTANCE / 'runs/round-20-descriptive-reference-headings/r20-live'
prior_audit = json.loads(previous.joinpath('audit.json').read_text())
evidence_names = ['summary.json','search-matrix.csv','gpt-web-answers.jsonl','codex-answers-complete.jsonl','tavily-answers.jsonl','exa-answers.jsonl']
for name in evidence_names:
    assert digest(previous / name) == prior_audit['sha256'][name]
write('source-evidence-manifest.json',{'source_round':20,'source_status':'Complete real 60-cell immediate observation; not new R21 searches',
    'files':{name:{'path':'../round-20-descriptive-reference-headings/r20-live/' + name,'sha256':digest(previous / name)} for name in evidence_names},
    'control_matrix_sha256':digest(ROOT / 'control/search-matrix.csv'),
    'limit':'Displayed URLs motivate an entry-surface test, not lift, indexing, traffic or causal module effects'})
evidence = json.loads(ROOT.joinpath('r20-search-evidence.json').read_text())
assert all((DEST / p).resolve().is_file() for row in evidence['observations'] for p in row['raw_files'].values())
jobs = ['1856605','1856612','1856638']
accounting = subprocess.check_output(['sacct','--jobs',','.join(jobs),'--noheader','--parsable2','--format=JobIDRaw,JobName,State,ExitCode'],text=True)
write('slurm-provenance.json',{'selection_job':jobs[0],'seed_and_allocation_job':jobs[1],'validation_job':jobs[2],
    'archive_job':os.environ['SLURM_JOB_ID'],'accounting_before_archive_completion':accounting,
    'resources':'CPU only, account aip-xiye17, 1 CPU, 1 GB, 5 minutes per job; all job I/O in scratch',
    'login_actions':'Light Git/curl/read-only inspection only; no Python, Node, compilation, local inference or new paid searches'})
ROOT.joinpath('README.md').write_text(f'''# EAU R21 — retained static second-backbone evidence on R18

Status: **validated local candidate; not published or measured**.

- Run: {run['run_id']}; sequential, one exact retained table insertion.
- Candidate: {change['candidate_commit']}.
- Tree: {change['candidate_tree']}.
- Seed: best complete R18 {change['selection_seed_commit']}.
- Historical control: original R18 12/60 citations, primary 20.00/100;
  secondary report-only composite 35.19444. Not a fresh simultaneous control.
- Production remains unchanged R20 {change['current_production_commit']}:
  12/60, primary 20.00, secondary 34.83333, discard tie.
- Keep requires all 60 valid and strictly more than 12/60; ties discard.

## Why this separate combination

R19 metadata and R20 reference-page H1 bundles both tied R18's twelve citation
cells. In the actual complete R20 output, nine cells explicitly return the
homepage URL; five return support-page URLs. Fuzzy citations are 2/20 and broad
citations 1/20 under the frozen judge, not all explicit links. These observations
locate an entry surface and motivate testing existing static evidence, not an
estimate that a table will improve retrieval. R20 source URLs and pointers to
all four original raw answer files are in r20-search-evidence.json. Their hashes
are in source-evidence-manifest.json. No new R21 search probes were issued.

R21 replays the exact final retained R14 manifest on best R18. It inserts one
default-open, separately labelled Qwen2.5-7B-Instruct reference table into the
existing results section. All nine methods and 36 values are independently
parsed from the unchanged results.qwen25 JS data, preserving three-decimal
precision, column order and model label. No new experiment, result, percentage
gain, tau2 value, affiliation, date or research claim is introduced.

The original Qwen3 charts/table, default selection, switch buttons, main renderer
targets and noscript fallback are untouched. The new table has separate IDs and
caption; it is not a renderer target. Existing details/table-scroll styles are
reused. No browser/visual test was performed; unchanged selectors/styles are
structural checks, not proof of layout or interactive behavior.

R14's original 5/60 against historical R9 8/60 remains a discard. R15, which
bundled the R12 H1, R13 static method and R14 table on R9 and measured 6/60,
also remains unchanged. R21 is not a replay of R15: it keeps the original H1,
R16 H2s, R17 static method and R18 alphaXiv routes, and newly adds only the exact
R14 table. Parents are R18/R14. No old score is added, averaged or inherited to
predict this new observation. combination-source.json and parents/ preserve the
exact original manifest, JS-derived data and old measured record. The old
R9→R14 HTML was reproduced exactly from that one manifest before selecting it.

## Exact scope and production difference

Only index.html changes relative to R18, solely by the one R14 insertion.
Removing that exact block recovers R18 byte-for-byte. R16 H2s and R17 static
components, all other sections, all HTML heads/JSON-LD, original result rows,
citation/PDF/BibTeX, scripts/styles/assets, reference pages, crawler files,
README, llms.txt and site-config.js are unchanged versus the R18 seed.
All nine R18 alphaXiv routing operations and six HTML reading anchors remain.
Scholarly arXiv identifiers and references remain intact. Neither external
domain counts as a project-site citation, and alphaXiv traffic is unmeasured.

Current production is R20, not the best R18 seed. A future approved deployment
therefore changes THREE pages: add the table in index.html and restore the
original R18 method/context H1s instead of inheriting discarded R20 headings.
No R19 schema bundle is inherited. candidate.patch is the one-file seed diff;
production-to-candidate.patch is the full three-file production diff. Candidate
snapshots and unchanged served R20 resources are preserved. Production is not
rolled back or otherwise changed now.

## Validation and retained history

All {len(validation['checks'])} structural/factual checks passed. Homepage visible
text: {validation['visible_home_chars_before']} → {validation['visible_home_chars_after']}
characters, within the unchanged {validation['limit']} cap and 1.3× growth bound.
Checks independently cover exact parent replay/reversal, nine rows/36 values,
default model preservation, separate IDs/labels, unchanged non-result bytes,
alphaXiv routes, hidden text, JSON-LD, links/fragments and all frozen protocol
hashes. No inner score was computed. Existing geo-apply made one supported
file:index.html replacement inside the allocated worktree. Preview/applied
diffs and whole-file/results-section graph fingerprints match actual bytes.
No wrapper-core extension or manual support-file edit was needed.

module-review.json reviews all ten inventory modules and fourteen old proposals.
All twenty-one R0–R20 observations, all fourteen older proposals and best R18
remain unchanged. Fifteen proposals now exist; only R21 and external-authority
are unmeasured. Discard never deletes a candidate. This ledger is maintained by
the agent, not a background scheduler or automatic recombination algorithm.

The archived metric replays the original R18 result and rejects this unpublished
R21 tree with exit 2; no candidate score or crash is registered. Separate explicit
publication approval is required. Recheck then-current main for teammate changes,
verify the full candidate tree and all THREE changed served resources before
and after the frozen 15-query × GPT web / Codex / Tavily / Exa collection.
No memory dimension or inner metric. The unchanged settings file retains legacy
R9 wording; the registered control is original R18. Bare-domain citation cells
and explicit source URLs stay distinct. Immediate historical-control results
cannot isolate module effects, interactions or indexing lag.

All Python, wrapper CLI, source parsing, validation and archival checks ran via
Slurm. No site publication/push, new paid searches, rollback, cleanup, pruning,
deletion, automatic follow-up or next-round start was performed.
''')
names = ['README.md','change.json','production-context.json','validation.json','source-verification.json','combination-source.json',
    'source-evidence-manifest.json','observed-entry-surfaces.json','new-proposals.json','collection-settings.json','operations.json',
    'candidate.patch','production-to-candidate.patch','module-review.json','config.json','graph-before.json','graph-after.json',
    'priorities.json','decision.json','exploration.json','edit-mechanism.json','preview.json','applied.json',
    'candidate-pool-before.json','candidate-pool-selected.json','candidate-pool-after.json','outer-only-policy.json','outer_metric.py',
    'queries.txt','search-map.json','r20-search-evidence.json','wrapper-run.json','wrapper-candidate.json','seed-evaluation.json',
    'seed-record.json','unpublished-metric-guard.txt','common.py','prepare_r21.py','allocate_r21.py','candidate_r21.py',
    'archive_prepared_r21.py','select_candidate.sh','allocate_candidate.sh','prepare_candidate.sh','archive_candidate.sh',
    'slurm-provenance.json','wrapper-scan.txt','wrapper-configure.txt']
names += ['parents/' + p.name for p in sorted(ROOT.joinpath('parents').iterdir())]
names += ['control/' + n for n in ['summary.json','search-matrix.csv','search-map.json']]
names += ['served-r20/' + n for n in HTML]
paths = [(ROOT / n,DEST / n) for n in names]
paths += [(ROOT / 'portable-outer-measurements.json',DEST / 'outer-measurements.json')]
run_dir = SITE / '.autoresearch-wrapper/runs' / run['run_id']
paths += [(run_dir / n,DEST / n) for n in ['program.md','results.tsv']]
worktree = Path(change['candidate']['worktree_path'])
paths += [(worktree / n,DEST / 'site' / n) for n in HTML]
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
audit = {'passed':True,'local_checks':len(validation['checks']),'history_count':21,'old_proposals_preserved':14,
    'proposal_count':15,'unmeasured_proposals':2,'candidate_commit':change['candidate_commit'],'candidate_tree':change['candidate_tree'],
    'exact_r14_operations':1,'source_rows':9,'source_numeric_values':36,'changed_files_vs_r18':FILES,'changed_files_vs_live_r20':DEPLOY_FILES,
    'seed_metric_replay':seed.stdout.strip(),'candidate_guard_exit':guard.returncode,'archive_job':os.environ['SLURM_JOB_ID'],
    'outer_status':'Unmeasured R21; explicit approval, exact deployment and complete real collection required',
    'sha256':{p.relative_to(DEST).as_posix():digest(p) for p in sorted(DEST.rglob('*')) if p.is_file()}}
DEST.joinpath('audit.json').write_text(json.dumps(audit,indent=2) + '\n')
print(json.dumps({k:v for k,v in audit.items() if k != 'sha256'},indent=2))
