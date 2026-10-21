"""Archive the exact R22 measured version before a separate user visual release."""
import copy
import datetime as dt
import re
import shutil
import sys
from common import *

assert os.environ.get('SLURM_JOB_ID')
LIVE,ARCHIVE = ROOT / 'r22-live',DEST / 'r22-live'
assert not ARCHIVE.exists()
summary = json.loads(LIVE.joinpath('summary.json').read_text())
record = json.loads(LIVE.joinpath('wrapper-record.json').read_text())
deployment = json.loads(LIVE.joinpath('deployment.json').read_text())
change = json.loads(ROOT.joinpath('change.json').read_text())
before_pool = json.loads(ROOT.joinpath('candidate-pool-before-publication.json').read_text())
pool = json.loads(INSTANCE.joinpath('candidate-pool.json').read_text())
assert pool == before_pool and len(pool['history']) == 22 and len(pool['proposals']) == 16
assert summary['scheduled']['valid_responses'] == 60
assert record['status'] == summary['decision'] == ('keep' if summary['scheduled']['project_citations'] > 12 else 'discard')
assert git(PRODUCTION,'rev-parse','HEAD') == deployment['production_merge_commit'] and git(PRODUCTION,'rev-parse','HEAD^{tree}') == change['candidate_tree']
worktree = Path(change['candidate']['worktree_path'])

def save(name,obj):
    LIVE.joinpath(name).write_text(json.dumps(obj,ensure_ascii=False,indent=2) + '\n')

raw = [{'provider':p,'query_index':i,'request':json.loads(LIVE.joinpath(f'{p}-raw/{i:02d}-request.json').read_text()),
    'response':json.loads(LIVE.joinpath(f'{p}-raw/{i:02d}.json').read_text())} for p in ['tavily','exa'] for i in range(1,16)]
LIVE.joinpath('raw-api-responses.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False) + '\n' for r in raw))
gpt = [json.loads(LIVE.joinpath(f'gpt-web-raw/query-{i:02d}.json').read_text()) for i in range(1,16)]
LIVE.joinpath('gpt-web-raw-responses.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False) + '\n' for r in gpt))
save('deployment-propagation.json',{'attempts':[json.loads(l) for l in LIVE.joinpath('served-verification-attempts.jsonl').read_text().splitlines()],
    'gate':'All five changed served resources match before any eval query and again after all sixty complete',
    'collection_timing_verified':True,'first_stale_read_issued_no_search':True})
chosen = next(p for p in pool['proposals'] if p['id'] == SELECTED)
assert chosen['candidate_commit'] == deployment['candidate_commit'] == 'fae44609023fddc240a13502f77abcfcd925c95d' and chosen['measured'] is False
save('candidate-pool-before-record.json',pool)
chosen.update({'status':record['status'],'measured':True,'deployment_status':'live','production_commit':summary['production_merge_commit'],
    'measured_at':summary['measured_at'],'outer_observation':summary['scheduled'],'measurement_artifact_dir':'runs/round-22-paper-project-entry/r22-live',
    'interpretation':'Measured latest R22 code-release bundle against original historical R18; not an isolated paragraph/code-link effect. Original pre-amendment R22 remains unmeasured and preserved.'})
pool['history'].append({'id':'r22','round':22,'change_id':CHANGE_ID,'revision':'code-release','parents':['r18'],'files':FILES,
    'candidate_commit':deployment['candidate_commit'],'candidate_tree':deployment['production_tree'],'production_commit':summary['production_merge_commit'],
    'branch':deployment['source_branch'],'selection_seed_commit':change['selection_seed_commit'],'production_changed_files':DEPLOY_FILES,
    'outer_observation':summary['scheduled'],'decision':record['status'],'artifact_dir':'runs/round-22-paper-project-entry/r22-live',
    'retain_for_combinations':True,'status':'measured_bundle_not_isolated_module_effect'})
previous_best = copy.deepcopy(pool['best_observed'])
if record['status'] == 'keep':
    pool['best_observed'] = {'round':22,'change_id':CHANGE_ID,'candidate_commit':deployment['candidate_commit'],'candidate_tree':deployment['production_tree'],
        'production_commit':summary['production_merge_commit'],'metric_name':'live_project_citation_rate','metric_value':record['metric_value'],
        'outer_observation':summary['scheduled'],'measured_at':summary['measured_at'],'decision':'keep','artifact_dir':'runs/round-22-paper-project-entry/r22-live',
        'interpretation':'Highest complete observed primary metric; historical control, not causal lift or traffic.'}
pool['policy'].update({'baseline':f"Best complete observed R{pool['best_observed']['round']}; R22 used original R18 historical 12/60, not a fresh control",
    'current_production':f"R22 code-release live: {summary['scheduled']['project_citations']}/60, {record['status']}; exact measured tree in r22-live/deployment.json",
    'deployment':'R22 approved; complete candidate/production tree and all five changed served resources matched before and after sixty frozen real responses; no automatic rollback',
    'history':'All 23 R0–R22 observations and 16 proposals retained; 15 other proposals unchanged; only external-authority is unmeasured. Never add parent scores.',
    'user_code_release_constraint':'Retain https://github.com/StringNLPLAB/meta-agent as the user-supplied public Code destination in future website revisions, independently of GEO keep/discard; do not restore coming-soon labels.'})
pool['updated_at'] = dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')
save('candidate-pool-after-record.json',pool)
save('best-observed-selection.json',{'previous_best':previous_best,'selected_best':pool['best_observed'],'promoted':record['status'] == 'keep',
    'decision':record['status'],'rule':'All sixty valid and strictly more than R18 12/60; ties discard','no_automatic_rollback':True,
    'user_code_destination_retained':True,'later_visual_release_is_separate_unmeasured_version':True})
save('deployed-change.json',{**change,'state':'deployed_and_measured','production_merge_commit':summary['production_merge_commit'],'outer_selection':record['status']})
control = json.loads(ROOT.joinpath('control/summary.json').read_text())
body = f'''# EAU R22 code release — live outer test

Measured candidate `{deployment['candidate_commit']}`, production
`{summary['production_merge_commit']}`, tree `{deployment['production_tree']}`.
This is the latest amended R22, not the original aa3c0ea paragraph-only tree.
All five changed resources matched before {deployment['served_version_verified_at']}
and after {deployment['served_version_reverified_at']}; the first stale README
check gated every eval request. All request/group times lie inside these bounds.

## Result

Primary: {summary['scheduled']['project_citations']}/60,
{100*summary['scheduled']['citation_rate']:.2f}/100 versus original R18 12/60, 20.00.
Report-only composite: {summary['scheduled']['score']:.2f} versus R18 35.19
and R21 35.89. Valid: 60/60. Decision: **{record['status']}**.

| Engine | R18 citations | R22 citations | Valid |
| --- | ---: | ---: | ---: |
'''
for engine,stats in summary['by_engine'].items():
    body += f"| {engine} | {control['by_engine'][engine]['project_citations']}/15 | {stats['project_citations']}/15 | {stats['valid_responses']}/15 |\n"
body += '\nExact / fuzzy / broad citations: ' + ' / '.join(str(summary['by_tier'][t]['project_citations']) for t in ['exact','fuzzy','broad']) + ' (each /20).\n'
body += f'''Gained/lost citation cells: {len(summary['citation_transitions']['gained'])}/{len(summary['citation_transitions']['lost'])}.
Explicit project URL cells: {summary['explicit_project_url_cells']}/60;
support-page URL cells: {summary['explicit_support_page_url_cells']}/60.
Full transitions and URL evidence are in summary.json/explicit-project-urls.json.

## Scope and limitations

On R18: move the existing official-project paragraph inside paper.html; enable
two static homepage Code anchors; remove stale coming-soon labels; set codeUrl
and add Code resources to README and llms.txt. All five complete served files
are archived. Relative to previous R21, the discarded second-backbone table is
also removed to recover the selected R18 homepage. All paper/alphaXiv reading
routes, scholarly arXiv fields, facts, data, runtime and styles are preserved.
Original R22's 34-check snapshot and code-release revision's 28-check snapshot
remain intact. No inner metric or browser test.

Frozen 15 queries × GPT web / Codex search / Tavily / Exa; no memory dimension.
Strictly greater primary is required; a tie discards regardless of composite.
R18 is the original historical control, not a fresh simultaneous measurement.
The settings file retains legacy R9 wording; the actual registered control is R18.
The primary judge includes bare project-domain occurrences; explicit URLs remain
separate. Neither alphaXiv, arXiv nor GitHub code counts as a project citation.
No traffic was measured and no isolated paragraph/code-link effect is established.

One first-pass response per cell, no successful response selectively retried.
{sum(r['raw'].startswith('Empty search results') for r in gpt)} GPT responses explicitly reported no results; those real
nonempty tool responses are retained unchanged and count as no discovery, not
an excuse to resample. All 30 API requests returned HTTP 200. Original GPT raw
text, API JSON, Codex answers and request/group times are preserved. Network-only
curl/jq and the preinstalled native Codex binary collected responses; all Python,
normalization, scoring, wrapper CLI and archival work used Slurm. No login-node
Python, Node, compilation or local model inference. No compute proxy retry.

All 23 measured histories and 16 proposals remain; 15 other proposals and
their decisions are unchanged. Best R{pool['best_observed']['round']} remains selected.
Code links stay published regardless of the GEO tie. A user-requested black
theme/icon release will follow only after this exact measured version is locked;
that later tree is not measured by this matrix and must not inherit its score.
No automatic optimization round, pruning, deletion or rollback occurred.
'''
LIVE.joinpath('REPORT.md').write_text(body)
registry = json.loads(ROOT.joinpath('outer-measurements.json').read_text())
for r in registry['measurements']:
    if r['label'] == 'r18-best-reused-control':
        r['matrix'] = '../round-18-alphaxiv-paper-routing/r18-live/search-matrix.csv'
save('portable-outer-measurements.json',registry)
for name in ['README.md','CURRENT.json','outer-measurements.json']:
    shutil.copy2(DEST / name,LIVE / ('pre-live-' + name))
save('execution-context.json',{'preparation_job':'1875676','normalization_job':'1875692','scoring_job':'1875707','archive_job':os.environ['SLURM_JOB_ID'],
    'network_only':'GPT web tool, curl/jq, native Codex CLI; 8+7 groups, low, timeout90, unchanged prompt',
    'failed_served_check':'Retained; zero eval queries before complete before gate','new_visual_request':'Separate post-measurement release, not evaluated here'})
for name in ['publication-intent.json','wrapper-before-publication.json']:
    shutil.copy2(ROOT / name,LIVE / name)
scripts = ROOT.glob('*.py')
for p in [*scripts,*ROOT.glob('*.sh')]:
    LIVE.joinpath('scripts').mkdir(exist_ok=True)
    shutil.copy2(p,LIVE / 'scripts' / p.name)
for p in sorted(LIVE.rglob('*')):
    if p.is_file() and (p.parent == LIVE or 'scripts' in p.parts):
        assert not re.search(r'(?i)tvly-[a-z0-9_-]{16,}|authorization:\s*bearer\s+[a-z0-9_-]{16,}|x-api-key\s*:\s*[a-z0-9_-]{16,}',p.read_text()),p.name
paths = [p for p in sorted(LIVE.rglob('*')) if p.is_file() and not any(t in p.parts for t in ['tavily-raw','exa-raw','gpt-web-raw','answers.logs'])]
for source in paths:
    relative = source.relative_to(LIVE)
    target = ARCHIVE / relative
    target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(source,target)
shutil.copy2(SITE / '.autoresearch-wrapper/runs' / change['wrapper_run_id'] / 'results.tsv',ARCHIVE / 'results.tsv')
INSTANCE.joinpath('candidate-pool.json').write_text(json.dumps(pool,ensure_ascii=False,indent=2) + '\n')
DEST.joinpath('outer-measurements.json').write_text(json.dumps(registry,indent=2) + '\n')
DEST.joinpath('CURRENT.json').write_text(json.dumps({'round':22,'revision':'code-release','state':'deployed_and_measured','decision':record['status'],
    'production_commit':summary['production_merge_commit'],'production_tree':deployment['production_tree'],'candidate_commit':deployment['candidate_commit'],
    'primary_citations':f"{summary['scheduled']['project_citations']}/60",'report':'r22-live/REPORT.md','best_observed_round':pool['best_observed']['round'],
    'pending_visual_release':'User requested black background and icons; separate tree and no inherited measurement'},indent=2) + '\n')
DEST.joinpath('README.md').write_text(f"R22 code-release was published and measured: {summary['scheduled']['project_citations']}/60, {record['status']}; composite {summary['scheduled']['score']:.2f}. See [live report](r22-live/REPORT.md) and CURRENT.json. A later user-requested visual release is separate and unmeasured. The preparation record below is retained verbatim in r22-live/pre-live-README.md.\n\n" + ARCHIVE.joinpath('pre-live-README.md').read_text())
assert pool['history'][:-1] == before_pool['history'] and len(pool['history']) == 23
assert [p for p in pool['proposals'] if p['id'] != SELECTED] == [p for p in before_pool['proposals'] if p['id'] != SELECTED]
assert len(pool['proposals']) == 16 and {p['id'] for p in pool['proposals'] if not p.get('measured',False)} == {'external-paper-link-audit'}
if record['status'] == 'discard':
    assert pool['best_observed'] == before_pool['best_observed']
for name,sha in json.loads(REVISION.joinpath('audit.json').read_text())['sha256'].items():
    assert digest(REVISION / name) == sha,name
for name,sha in json.loads(DEST.joinpath('audit.json').read_text())['sha256'].items():
    p = REVISION / 'preimages' / name if name in ['README.md','CURRENT.json'] else ARCHIVE / 'pre-live-outer-measurements.json' if name == 'outer-measurements.json' else DEST / name
    assert digest(p) == sha,name
replays = {}
for name,citations in [('seed',12),('candidate-001',summary['scheduled']['project_citations'])]:
    p = subprocess.run([sys.executable,str(DEST / 'outer_metric.py')],cwd=worktree.parent / name,check=True,capture_output=True,text=True)
    assert f'LIVE_PROJECT_CITATIONS={citations}/60' in p.stdout
    replays[name] = p.stdout.strip()
assert deployment['production_tree'] == git(worktree,'rev-parse','HEAD^{tree}') == git(PRODUCTION,'rev-parse','HEAD^{tree}')
assert not git(PRODUCTION,'status','--porcelain') and not git(worktree,'status','--porcelain')
for phase in ['before','after']:
    for name,sha in deployment['resource_sha256'].items():
        assert digest(ARCHIVE / f'served-{phase}' / name) == sha
gpt_answers = [json.loads(l) for l in ARCHIVE.joinpath('gpt-web-answers.jsonl').read_text().splitlines()]
assert all(r['raw'] == a['text'] and r['query'] == a['query'] for r,a in zip(gpt,gpt_answers))
accounting = subprocess.check_output(['sacct','--jobs','1875676,1875692,1875707','--noheader','--parsable2','--format=JobIDRaw,JobName,State,ExitCode'],text=True)
ARCHIVE.joinpath('slurm-provenance.json').write_text(json.dumps({'completed_jobs':accounting,'archive_job':os.environ['SLURM_JOB_ID'],'resources':'1 CPU, 1 GB, 5 min; scratch I/O'},indent=2) + '\n')
audit = {'passed':True,'cells':60,'project_citations':summary['scheduled']['project_citations'],'candidate_commit':deployment['candidate_commit'],
    'production_commit':summary['production_merge_commit'],'measured_tree':deployment['production_tree'],'history_count':23,'proposal_count':16,
    'other_proposals_preserved':15,'served_resources':5,'all_times_bounded':True,'raw_gpt_text_identical_to_scored_text':True,
    'no_successful_response_resampled':True,'archived_metric_replays':replays,'best_observed_round':pool['best_observed']['round'],
    'original_preparation_and_code_release_hashes_preserved':True,'sha256':{p.relative_to(ARCHIVE).as_posix():digest(p) for p in sorted(ARCHIVE.rglob('*')) if p.is_file()}}
ARCHIVE.joinpath('audit.json').write_text(json.dumps(audit,indent=2) + '\n')
print(json.dumps({k:v for k,v in audit.items() if k != 'sha256'},indent=2))
