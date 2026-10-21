"""Append an auditable unmeasured R22 archive; preserve all prior candidates."""
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
assert pool['history'] == original['history'] and len(pool['history']) == 22 and all(h['retain_for_combinations'] for h in pool['history'])
assert len(pool['proposals']) == 16 and len(original['proposals']) == 15 and all(p in pool['proposals'] for p in original['proposals'])
assert pool['best_observed'] == original['best_observed'] and pool['best_observed']['round'] == 18
chosen = next(p for p in pool['proposals'] if p['id'] == SELECTED)
assert chosen['parents'] == ['r18'] and chosen['measured'] is False and 'outer_observation' not in chosen
assert {p['id'] for p in pool['proposals'] if not p.get('measured',False)} == {SELECTED,'external-paper-link-audit'}
assert next(p for p in pool['proposals'] if p['id'] == 'descriptive-static-evidence-combination')['status'] == 'discard'
assert git(PRODUCTION,'rev-parse','HEAD') == change['current_production_commit'] and not git(PRODUCTION,'status','--porcelain')
registry = json.loads(ROOT.joinpath('outer-measurements.json').read_text())
assert len(registry['measurements']) == 1 and registry['measurements'][0]['label'] == 'r18-best-reused-control'
registry['measurements'][0]['matrix'] = '../round-18-alphaxiv-paper-routing/r18-live/search-matrix.csv'
write('portable-outer-measurements.json',registry)
previous = INSTANCE / 'runs/round-21-descriptive-static-evidence-combination/r21-live'
prior_audit = json.loads(previous.joinpath('audit.json').read_text())
evidence_names = ['summary.json','search-matrix.csv','gpt-web-answers.jsonl','codex-answers-complete.jsonl','tavily-answers.jsonl','exa-answers.jsonl']
for name in evidence_names:
    assert digest(previous / name) == prior_audit['sha256'][name]
write('source-evidence-manifest.json',{'source_round':21,'source_status':'Complete actual 60-cell immediate observation; not new R22 searches',
    'files':{name:{'path':'../round-21-descriptive-static-evidence-combination/r21-live/' + name,'sha256':digest(previous / name)} for name in evidence_names},
    'control_matrix_sha256':digest(ROOT / 'control/search-matrix.csv'),
    'limit':'Displayed URLs/snippets motivate placement only; no causal, indexing, traffic or uplift claim'})
evidence = json.loads(ROOT.joinpath('r21-search-evidence.json').read_text())
assert all((DEST / p).resolve().is_file() for row in evidence['observations'] for p in row['raw_files'].values())
jobs = ['1874074','1874084','1874087']
accounting = subprocess.check_output(['sacct','--jobs',','.join(jobs),'--noheader','--parsable2','--format=JobIDRaw,JobName,State,ExitCode'],text=True)
write('slurm-provenance.json',{'selection_job':jobs[0],'seed_and_allocation_job':jobs[1],'validation_job':jobs[2],
    'archive_job':os.environ['SLURM_JOB_ID'],'accounting_before_archive_completion':accounting,
    'resources':'CPU only, account aip-xiye17, 1 CPU, 1 GB, 5 minutes per job; job I/O in scratch',
    'login_actions':'Light Git/curl/jq/read and apply_patch only; no Python, Node, compilation, local inference or paid searches'})
ROOT.joinpath('README.md').write_text(f'''# EAU R22 — project entry beside the paper identity

Status: **validated local candidate; not published or measured**.

- Run: {run['run_id']}; target paper.html, sequential, one candidate.
- Candidate: {change['candidate_commit']}.
- Tree: {change['candidate_tree']}.
- Seed: best observed R18 {change['selection_seed_commit']}.
- Original R18 historical control: 12/60 project-domain citation cells,
  primary 20.00/100, report-only composite 35.19444. Not a fresh control.
- Production remains R21 {change['current_production_commit']}, unchanged:
  12/60, primary 20.00, report-only composite 35.88889, discard tie.
- Keep requires all sixty valid and strictly more than 12/60; ties discard.

## Entry evidence and selected experiment

R19, R20 and R21 tied R18 on the locked primary metric. R21 gained one fuzzy
Codex cell and lost one exact Codex cell (8/3/1 exact/fuzzy/broad, versus 9/2/1
for R18). Its higher secondary score and fuzzy count do not make it the seed.

The saved R21 Exa answers explicitly return paper.html in three cells: paper
identifier, meta-agent identity and benchmark queries. Their actual displayed
paper snippets include identity/results text, not the official-project paragraph
in the footer. observed-entry-surfaces.json preserves those snippets and exact
source cells; r21-search-evidence.json reduces actual URLs from all four engines,
with pointers to original answers. source-evidence-manifest.json hashes the
complete prior raw files and distinct R21/R18 matrices. No new R22 probes ran.

The official-home link already exists and was independently inspected in the
served R21 paper page. This is **not a missing edge** or external backlink fix.
Move that single existing paragraph, verbatim, from the references footer into
the identity overview-copy immediately after the existing evaluation sentence.
Placement nearer the paper identity may make the existing route easier to
extract; snippet omission does not establish a cause or predict improvement.
The paper URL itself already counts as a project-domain citation when returned.
Do not count the relocation as a new citation without a new real observation.

The new candidate's parent is R18. R18 includes the prior reference routes,
R16 headings, R17 static method and user-requested alphaXiv routing. All fifteen
old proposals remain unchanged, including R21's original primary tie/fuzzy
gain/exact loss, R14/R15 discards and the unverified external-authority proposal.
Old candidates remain available for future explicit combinations; no parent
scores are added, averaged or promoted by a secondary metric.

## Exact scope and production difference

Only paper.html differs from R18. Two text spans implement one paragraph move;
the inverse recovers every seed byte. The paragraph's text, href, class and
number of occurrences stay unchanged. The head/JSON-LD, bibliographic fields,
authors, affiliations, evidence values, headings, navigation, three footer
support links and all other page content remain unchanged. No new fact, result,
keyword padding, link, hidden text, script, style, identifier or URL is added.
The graph identifies file:paper.html as an asset with operations:[]; the main
agent used apply_patch in the allocated worktree after reading program.md.
No unsupported geo-apply operation or wrapper-core modification is claimed.

Every other tracked website file is byte-identical to R18, including index,
method/context pages, scripts/styles, default model/switch data, llms.txt,
README, citations, robots and sitemap. All nine R18 alphaXiv routing operations
and six HTML reading anchors remain; scholarly arXiv IDs/PDF/BibTeX/JSON-LD
references are unchanged. Neither external domain is a project citation, and
alphaXiv traffic remains unmeasured.

Production is R21, not the best seed. A future separately approved deployment
therefore changes TWO pages relative to current main: restore the R18 homepage
by removing the discarded R21 second-backbone table, and move the paper-page
paragraph. No R19 schema or R20 H1 bundle is inherited. candidate.patch is the
one-file seed diff; production-to-candidate.patch preserves the full two-file
production diff. This preparation did not roll back or change production.

## Validation, state and next gate

All {len(validation['checks'])} structural/factual checks passed. Homepage visible
text stays {validation['visible_home_chars_after']} characters under the locked
{validation['limit']} cap; paper visible text stays
{validation['visible_paper_chars_after']} characters, with an identical word
multiset and identical href counts. Checks cover exact reversal, correct
identity/footer placement, balanced paper HTML, local paths/fragments, unique
IDs, JSON-LD, alphaXiv routing, whole-tree scope and unchanged frozen
map/query/judge/normalizer/settings/original R18 matrix. The graph paper content
fingerprint matches actual bytes and is the only changed node fingerprint.
No inner metric or browser/visual test was run; structural checks and unchanged
classes do not establish rendered layout or search behavior.

module-review.json reviews all ten inventory modules and fifteen older
proposals. All twenty-two R0–R21 historical observations and best R18 remain
unchanged. Sixteen proposals now exist, fourteen measured and two unmeasured
(R22 and external-authority). The agent maintains the ledger; no background
scheduler or automatic candidate-recombination behavior is implied.

The archived scorer replays the original R18 12/60 and rejects the exact R22
tree with exit 2, without registering an unpublished candidate score or crash.
The CLI run remains active with one allocated, locally committed candidate;
after explicit publication approval, resume that same run, recheck then-current
main and teammate changes, verify the full candidate tree and BOTH changed
served resources before/after the frozen 15-query × GPT web / Codex / Tavily /
Exa collection. No memory dimension. The byte-identical settings file retains
legacy R9 wording; the actual registered historical control is R18.

Bare-domain citation cells and explicit source URLs are distinct. A single
immediate historical comparison cannot isolate module contribution, rule out
search variance/indexing lag or establish traffic changes. No site push/merge,
paid queries, rollback, deletion/pruning, finalization, automatic follow-up or
next-round start occurred. All Python, CLI, parsing, validation and archival
work ran as Slurm jobs, with scratch job I/O.
''')
names = ['README.md','change.json','production-context.json','validation.json','source-verification.json','source-evidence-manifest.json',
    'observed-entry-surfaces.json','new-proposals.json','collection-settings.json','edit-plan.json','candidate.patch','production-to-candidate.patch',
    'module-review.json','config.json','graph-before.json','graph-after.json','priorities.json','decision.json','exploration.json','edit-mechanism.json',
    'candidate-pool-before.json','candidate-pool-selected.json','candidate-pool-after.json','outer-only-policy.json','outer_metric.py',
    'queries.txt','search-map.json','r21-search-evidence.json','wrapper-run.json','wrapper-candidate.json','seed-evaluation.json','seed-record.json',
    'unpublished-metric-guard.txt','common.py','prepare_r22.py','allocate_r22.py','validate_r22.py','archive_r22.py','run_stage.sh',
    'slurm-provenance.json','wrapper-scan.txt','wrapper-configure.txt']
names += ['parents/' + p.name for p in sorted(ROOT.joinpath('parents').iterdir())]
names += ['control/' + n for n in ['summary.json','search-matrix.csv','search-map.json']]
names += ['served-r21/' + n for n in HTML]
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
status = json.loads(cli('status','--json',name='wrapper-status.json'))
active = status['runs'][run['run_id']]
assert active['status'] == 'active' and active['candidates']['candidate-001']['lifecycle'] == 'allocated'
DEST.joinpath('wrapper-status.json').write_text(json.dumps(status,indent=2) + '\n')
DEST.joinpath('CURRENT.json').write_text(json.dumps({'round':22,'state':change['state'],'published':False,'measured':False,
    'candidate_commit':change['candidate_commit'],'candidate_tree':change['candidate_tree'],'best_observed_round':18,'current_production_round':21},indent=2) + '\n')
audit = {'passed':True,'local_checks':len(validation['checks']),'history_count':22,'old_proposals_preserved':15,
    'proposal_count':16,'unmeasured_proposals':2,'candidate_commit':change['candidate_commit'],'candidate_tree':change['candidate_tree'],
    'semantic_relocations':1,'text_spans':2,'new_words':False,'new_links':False,'changed_files_vs_r18':FILES,'changed_files_vs_live_r21':DEPLOY_FILES,
    'seed_metric_replay':seed.stdout.strip(),'candidate_guard_exit':guard.returncode,'archive_job':os.environ['SLURM_JOB_ID'],
    'outer_status':'Unmeasured R22; explicit approval, exact deployment and complete real collection required',
    'sha256':{p.relative_to(DEST).as_posix():digest(p) for p in sorted(DEST.rglob('*')) if p.is_file()}}
DEST.joinpath('audit.json').write_text(json.dumps(audit,indent=2) + '\n')
print(json.dumps({k:v for k,v in audit.items() if k != 'sha256'},indent=2))
