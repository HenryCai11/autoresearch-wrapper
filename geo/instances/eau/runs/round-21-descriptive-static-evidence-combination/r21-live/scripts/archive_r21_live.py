"""Append the complete real R21 observation without changing any older candidate."""
import copy
import datetime as dt
import re
import shutil
from common import *

assert os.environ.get('SLURM_JOB_ID')
LIVE,ROUND,ARCHIVE = ROOT / 'r21-live',DEST,DEST / 'r21-live'
assert not ARCHIVE.exists(), 'Append-only live archive refuses overwrite'
summary = json.loads(LIVE.joinpath('summary.json').read_text())
record = json.loads(LIVE.joinpath('wrapper-record.json').read_text())
deployment = json.loads(LIVE.joinpath('deployment.json').read_text())
change = json.loads(ROOT.joinpath('change.json').read_text())
control = json.loads(ROOT.joinpath('control/summary.json').read_text())
before,after = summary['matched_valid_comparison']['baseline'],summary['matched_valid_comparison']['r21']
assert summary['scheduled']['valid_responses'] == before['n'] == after['n'] == 60
assert before['project_citations'] == 12
assert record['status'] == summary['decision'] == ('keep' if after['project_citations'] > 12 else 'discard')

def save(name,value):
    LIVE.joinpath(name).write_text(json.dumps(value,ensure_ascii=False,indent=2) + '\n')

raw = []
for provider in ['tavily','exa']:
    for i in range(1,16):
        raw.append({'provider':provider,'query_index':i,
            'request':json.loads(LIVE.joinpath(f'{provider}-raw/{i:02d}-request.json').read_text()),
            'response':json.loads(LIVE.joinpath(f'{provider}-raw/{i:02d}.json').read_text())})
LIVE.joinpath('raw-api-responses.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False) + '\n' for r in raw))
gpt = [json.loads(LIVE.joinpath(f'gpt-web-raw/query-{i:02d}.json').read_text()) for i in range(1,16)]
assert all(isinstance(r['raw'],str) and r['raw'].strip() for r in gpt)
LIVE.joinpath('gpt-web-raw-responses.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False) + '\n' for r in gpt))
attempts = [json.loads(line) for line in LIVE.joinpath('served-verification-attempts.jsonl').read_text().splitlines()]
save('deployment-propagation.json',{'attempts':attempts,'search_gate':'All three changed served resources must match before any search, then match again after every request completes',
    'collection_timing_verified':deployment['collection_timing_verified']})
body = f'''# EAU R21 — retained second-backbone evidence on R18, live outer test

Published as `{summary['production_merge_commit']}`. Complete candidate and
production trees match. All three changed served HTML resources matched before
collection ({deployment['served_version_verified_at']}) and after every request
finished ({deployment['served_version_reverified_at']}). The initial served
check saw old content; no eval search was issued until all three resources matched.

## One retained insertion and explicit production scope

Parents are R18/R14. Relative to best R18, only the exact final R14 static table
is inserted in index.html. It displays nine Qwen2.5-7B-Instruct method rows and
36 existing JS values, independently verified at unchanged three-decimal precision.
The original Qwen3 charts/table, model switch/default, original H1, R16 H2s,
R17 static method reference and all other original bytes are preserved. The new
default-open table has its own caption and IDs and is not a renderer target.
Scripts, styles, metadata/JSON-LD, result claims, citations/PDF/BibTeX, reference
pages, summaries, assets, crawler files and all alphaXiv reading routes remain
unchanged versus R18. No new experiment, result, gain or factual claim was added.

The original R14 5/60 discard against R9 and R15 6/60 multi-bundle discard remain
unchanged. This is not a replay of R15's R12 H1/method/table combination; R21
retains R18's original H1, R16 H2s, R17 method and alphaXiv routes. No parent
score is added, averaged or inherited. Exact parent artifacts and provenance
remain in the preparation archive. All 39 structural/factual checks passed;
homepage visible text is 6103 → 6676 within the frozen 9000 cap. No inner score
or browser/visual test was performed. Existing geo-apply made one supported
file:index.html replacement in an allocated worktree; no wrapper-core change.

R20 was live before deployment, so the approved production diff spans THREE
pages: add the table to index.html and restore R18 method/context H1s instead
of inheriting the discarded R20 heading bundle. No R19 schema bundle is inherited.
The one-file seed diff, three-file production diff and exact full tree are archived.

## Frozen historical comparison

Control is original R18 12/60 at 2026-10-19T09:14:05Z, not the distinct R20
matrix or a fresh simultaneous control. Same 15 queries × GPT web, Codex search,
Tavily and Exa; no memory dimension. Keep requires all 60 valid and strictly
more than 12/60; ties discard. The unchanged settings file retains legacy R9
wording; the registered actual control is R18.

| Engine | R18 citations | R21 citations | R21 valid |
| --- | ---: | ---: | ---: |
'''
for engine,stats in summary['by_engine'].items():
    body += f"| {engine} | {control['by_engine'][engine]['project_citations']}/15 | {stats['project_citations']}/15 | {stats['valid_responses']}/15 |\n"
body += f'''
Primary: **{before['project_citations']}/60 → {after['project_citations']}/60**
({100*before['citation_rate']:.2f}% → {100*after['citation_rate']:.2f}%).
Secondary legacy composite, report-only: {before['score']:.2f} → {after['score']:.2f}.
Citation cells gained/lost: {len(summary['citation_transitions']['gained'])}/{len(summary['citation_transitions']['lost'])}.
Explicit project URL cells: {summary['explicit_project_url_cells']}/60;
explicit support-page URL cells: {summary['explicit_support_page_url_cells']}/60.
Wrapper decision: **{record['status']}**.

The frozen judge includes bare project-domain occurrences, not always explicit
source links. URL/rank fields and explicit-project-urls.json keep that distinction.
alphaXiv/arXiv do not count as project citations; no alphaXiv traffic was measured.
These search tools are not interchangeable with consumer chat-app products.

## Collection, selection and retained history

One first-pass sample per cell; no successful answer selectively retried. Full
raw API replies, original GPT tool text and Codex output are retained with
request/group times bounded by the successful served-byte checks. Network-only
acquisition uses curl/jq and the same preinstalled native Codex binary. All Python,
normalization, scoring, wrapper CLI and audits use Slurm. No Node, Python,
compilation or local model inference ran on the login node. R20's already
documented compute proxy restriction was not bypassed or retried for this round.

This immediate sample against a historical control cannot isolate table effects,
interactions, search variation or indexing lag. R21 remains live without automatic
rollback regardless of selection. All twenty-one older R0–R20 observations,
fourteen older proposals and their original decisions are unchanged; R21 adds
the twenty-second observation. Fifteen proposals remain, only external-authority
is unmeasured. All candidates remain available for future combinations.
No external page edit, pruning, deletion, next round or follow-up was performed.
'''
LIVE.joinpath('REPORT.md').write_text(body)
pool = json.loads(INSTANCE.joinpath('candidate-pool.json').read_text())
original = json.loads(ROOT.joinpath('candidate-pool-before.json').read_text())
assert pool['current_round'] == 21 and pool['selected_candidate_id'] == SELECTED
assert pool['history'] == original['history'] and len(pool['history']) == 21 and len(pool['proposals']) == 15
assert all(p in pool['proposals'] for p in original['proposals'])
save('candidate-pool-before-record.json',pool)
chosen = next(p for p in pool['proposals'] if p['id'] == SELECTED)
assert chosen['parents'] == ['r18','r14'] and chosen['measured'] is False
chosen.update({'status':record['status'],'measured':True,'deployment_status':'live',
    'interpretation':'Measured exact retained R14 table on R18 as a separate combination; immediate historical comparison, not isolated table lift. All older candidates and alphaXiv routes retained.',
    'production_commit':summary['production_merge_commit'],'measured_at':summary['measured_at'],'outer_observation':summary['scheduled'],
    'measurement_artifact_dir':'runs/round-21-descriptive-static-evidence-combination/r21-live','retain_for_combinations':True})
assert not any(h['id'] == 'r21' for h in pool['history'])
pool['history'].append({'id':'r21','round':21,'change_id':CHANGE_ID,'files':FILES,'parents':['r18','r14'],
    'candidate_commit':deployment['candidate_commit'],'production_commit':summary['production_merge_commit'],'branch':deployment['source_branch'],
    'production_changed_files':DEPLOY_FILES,'selection_seed_commit':change['selection_seed_commit'],'outer_observation':summary['scheduled'],
    'decision':record['status'],'artifact_dir':'runs/round-21-descriptive-static-evidence-combination','retain_for_combinations':True,
    'status':'measured_combination_not_isolated_module_effect'})
previous_best = copy.deepcopy(pool['best_observed'])
assert previous_best == original['best_observed'] and previous_best['round'] == 18
if record['status'] == 'keep':
    pool['best_observed'] = {'round':21,'change_id':CHANGE_ID,'candidate_commit':deployment['candidate_commit'],
        'candidate_tree':summary['production_tree'],'production_commit':summary['production_merge_commit'],
        'metric_name':'live_project_citation_rate','metric_value':record['metric_value'],'outer_observation':summary['scheduled'],
        'measured_at':summary['measured_at'],'decision':'keep','artifact_dir':'runs/round-21-descriptive-static-evidence-combination/r21-live',
        'interpretation':'Highest complete observed primary metric; immediate historical control, not causal table lift or alphaXiv traffic.'}
pool['policy'].update({'baseline':f"Best complete historical observation: R{pool['best_observed']['round']} {pool['best_observed']['outer_observation']['project_citations']}/60. R21 was compared with original R18 12/60; no fresh simultaneous control.",
    'current_production':f"R21 live: {after['project_citations']}/60, {record['status']}; historical R18 12/60; alphaXiv routes retained",
    'deployment':'R21 explicitly approved; exact complete candidate tree and all three changed served pages verified before and after all sixty real samples. No automatic rollback.',
    'history':'All twenty-two R0–R21 observations and fifteen proposals retained; all fourteen older proposals unchanged. Only external-authority is unmeasured. Never add parent scores.'})
pool['updated_at'] = dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')
save('best-observed-selection.json',{'previous_best':previous_best,'selected_best':pool['best_observed'],'promoted':record['status'] == 'keep',
    'decision':record['status'],'rule':'All 60 valid and strictly more than 12/60; ties discard',
    'comparison_control':'Original historical R18 2026-10-19T09:14:05Z, not R20 or fresh simultaneous samples',
    'evidence':['summary.json','wrapper-record.json','deployment.json'],'routing_constraint':pool['policy']['user_routing_constraint'],'no_new_round_started':True})
save('candidate-pool-after-record.json',pool)
registry = json.loads(ROOT.joinpath('outer-measurements.json').read_text())
for r in registry['measurements']:
    if r['label'] == 'r18-best-reused-control':
        r['matrix'] = '../round-18-alphaxiv-paper-routing/r18-live/search-matrix.csv'
save('portable-outer-measurements.json',registry)
save('pre-live-outer-measurements.json',json.loads(ROUND.joinpath('outer-measurements.json').read_text()))
shutil.copy2(ROUND / 'README.md',LIVE / 'pre-live-README.md')
change.update({'state':'deployed_and_measured','production_merge_commit':summary['production_merge_commit'],'outer_selection':record['status'],
    'selection_record':'r21-live/wrapper-record.json','authorization':'User explicitly approved publishing and testing prepared R21'})
save('deployed-change.json',change)
names = ['REPORT.md','best-observed-selection.json','run.json','summary.json','comparison-vs-r18.json','deployment.json',
    'deployment-propagation.json','published.json','queries.txt','search-map.json','search-matrix.csv','search-probes.jsonl',
    'discovery.json','discovery.md','gpt-web-answers.jsonl','gpt-web-raw-responses.jsonl','codex-answers-complete.jsonl',
    'tavily-answers.jsonl','exa-answers.jsonl','network-events.jsonl','raw-api-responses.jsonl','explicit-project-urls.json',
    'collection-settings.json','outer-measurements-after-r21.json','wrapper-resume.json','wrapper-evaluation.json','wrapper-record.json',
    'wrapper-status.json','origin-main-before.txt','origin-main-after.txt','verified-before.txt','verified-after.txt',
    'served-verification-attempts.jsonl','candidate-pool-before-record.json','candidate-pool-after-record.json',
    'portable-outer-measurements.json','pre-live-outer-measurements.json','pre-live-README.md','deployed-change.json','execution-context.json']
names += [f'codex-group-{g}/{n}' for g in [1,2] for n in ['queries.txt','started-at.txt','completed-at.txt']]
names += [f'served-{phase}/{n}' for phase in ['before','after'] for n in DEPLOY_FILES]
for name in names:
    assert LIVE.joinpath(name).is_file(),name
    assert not re.search(r'(?i)tvly-[a-z0-9_-]{16,}|authorization:\s*bearer\s+[a-z0-9_-]{16,}|x-api-key\s*:\s*[a-z0-9_-]{16,}',LIVE.joinpath(name).read_text()),name
save('integrity.json',{'query_sha256':summary['query_sha256'],'sha256':{n:digest(LIVE / n) for n in names},
    'baseline_matrix_sha256':digest(ROOT / 'control/search-matrix.csv'),'served_resources_sha256':deployment['resource_sha256']})
names.append('integrity.json')
for name in names:
    target = ARCHIVE / name
    target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(LIVE / name,target)
INSTANCE.joinpath('candidate-pool.json').write_text(json.dumps(pool,ensure_ascii=False,indent=2) + '\n')
ROUND.joinpath('outer-measurements.json').write_text(json.dumps(registry,ensure_ascii=False,indent=2) + '\n')
ROUND.joinpath('CURRENT.json').write_text(json.dumps({'state':'deployed_and_measured','production_commit':summary['production_merge_commit'],
    'decision':record['status'],'primary_citations':f"{after['project_citations']}/60",'report':'r21-live/REPORT.md',
    'preparation_snapshot':'change.json','live_change':'r21-live/deployed-change.json'},indent=2) + '\n')
ROUND.joinpath('README.md').write_text(f"R21 is now published and measured: **{after['project_citations']}/60; {record['status']}**. See [live report](r21-live/REPORT.md), [selection](r21-live/best-observed-selection.json) and [CURRENT.json](CURRENT.json). The following is the original preparation record; its unchanged copy is r21-live/pre-live-README.md.\n\n" + LIVE.joinpath('pre-live-README.md').read_text())
run = json.loads(ROOT.joinpath('wrapper-run.json').read_text())
shutil.copy2(SITE / '.autoresearch-wrapper/runs' / run['run_id'] / 'results.tsv',ARCHIVE / 'results.tsv')
print(json.dumps({'archive':str(ARCHIVE),'decision':record['status'],'citations':after['project_citations'],
    'primary':100*after['citation_rate'],'secondary_composite':after['score'],'history_count':len(pool['history']),'best_round':pool['best_observed']['round']},indent=2))
