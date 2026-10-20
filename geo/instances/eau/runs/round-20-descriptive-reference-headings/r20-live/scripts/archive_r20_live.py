"""Append real R20 outer evidence; preserve every older candidate and result."""
import copy
import datetime as dt
import re
import shutil
from common import *

assert os.environ.get('SLURM_JOB_ID')
LIVE,ROUND,ARCHIVE = ROOT / 'r20-live',DEST,DEST / 'r20-live'
assert not ARCHIVE.exists(), 'Refuse to overwrite a live archive'
summary = json.loads(LIVE.joinpath('summary.json').read_text())
record = json.loads(LIVE.joinpath('wrapper-record.json').read_text())
deployment = json.loads(LIVE.joinpath('deployment.json').read_text())
change = json.loads(ROOT.joinpath('change.json').read_text())
control = json.loads(ROOT.joinpath('control/summary.json').read_text())
before,after = summary['matched_valid_comparison']['baseline'],summary['matched_valid_comparison']['r20']
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
save('deployment-propagation.json',{'attempts':attempts,'initial_stale_page':True,
    'search_gate':'No valid search samples issued before all four changed pages matched; final successful check after all requests',
    'collection_timing_verified':deployment['collection_timing_verified']})
body = f'''# EAU R20 — descriptive reference H1s, live outer measurement

Published as `{summary['production_merge_commit']}`. Complete candidate and
production trees match. All four changed served HTML resources matched before
collection ({deployment['served_version_verified_at']}) and after all requests
finished ({deployment['served_version_reverified_at']}). The initial served
check saw old content; no valid samples were requested until all four matched.

## Intervention and scope

Seed is best R18, not tied/discarded R19. Relative to R18, exactly two H1s change:
method: “How EAU adapts the training system.”; research context: “EAU as an
adaptive training system.” The first exactly reuses the existing R16 homepage
H2 wording on a new page/heading level; the second uses its existing lead phrase.
Parent is R18 only. No existing paragraph, secondary heading, result, citation,
PDF/BibTeX, HTML head or JSON-LD differs from R18. All alphaXiv reading routes,
machine summaries, scripts, styles, assets and crawler files are retained.

Since R19 was live before deployment, the approved production diff spans four
HTML pages: remove the discarded R19 schema bundle and apply the two H1s.
This is not a two-file change versus live R19. The exact candidate and full
four-file production patches are preserved in the preparation archive.
All 36 structural/factual checks passed; homepage remains 6103 visible chars.
Both files are graph-fingerprinted assets without text operations; exact edits
used apply_patch in an allocated worktree, not a wrapper-core extension.
No inner metric or browser/visual test was performed.

## Frozen historical comparison

Control is original R18 12/60, measured 2026-10-19T09:14:05Z; it is not a fresh
simultaneous control or the distinct tied R19 matrix. Same 15 queries × GPT web,
Codex search, Tavily and Exa, no memory dimension. Keep requires all 60 valid
and strictly more than 12/60 citation cells; ties discard. The unchanged
settings file retains legacy R9 wording; the registry specifies actual R18.

| Engine | R18 citations | R20 citations | R20 valid |
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

The frozen judge includes bare project-domain occurrences; they are not always
explicit source links. See URL/rank fields and explicit-project-urls.json.
alphaXiv/arXiv are not the project domain; no alphaXiv traffic was measured.
These four search tools are not interchangeable with consumer chat apps.

## Execution failures and retained evidence

The first compute-node API attempt had thirty proxy CONNECT failures (HTTP 000,
curl exit 56) and no API responses. The first fifteen Codex processes failed
before startup because Node was missing. Failed attempts are retained separately,
never scored as successful absent-project answers. recovery-notes.json records
the recovery route. The fifteen successful GPT samples were never retried.
No successful answer from any provider was selectively resampled. Network-only
API acquisition uses curl/jq; Python normalization, scoring and wrapper CLI use
Slurm. All sixty accepted samples must fall within the successful served checks.

This immediate observation against a historical control cannot isolate heading
effects, interactions, search variation or indexing lag. R20 remains live
without automatic rollback regardless of selection. All twenty older R0–R19
observations, thirteen older proposals and their original decisions are retained;
R20 adds the twenty-first observation without rewriting them. Fourteen proposals
remain, with only the external-authority proposal unmeasured. All candidates
remain available for future combinations; parent scores are not added.
No external page edit, pruning, cleanup, next round or follow-up was performed.
'''
LIVE.joinpath('REPORT.md').write_text(body)
pool = json.loads(INSTANCE.joinpath('candidate-pool.json').read_text())
original = json.loads(ROOT.joinpath('candidate-pool-before.json').read_text())
assert pool['current_round'] == 20 and pool['selected_candidate_id'] == SELECTED
assert pool['history'] == original['history'] and len(pool['history']) == 20 and len(pool['proposals']) == 14
assert all(p in pool['proposals'] for p in original['proposals'])
save('candidate-pool-before-record.json',pool)
selected = next(p for p in pool['proposals'] if p['id'] == SELECTED)
selected.update({'status':record['status'],'measured':True,'deployment_status':'live',
    'interpretation':'Measured two-heading bundle on best R18; immediate historical comparison, not isolated causal contribution. All alphaXiv routes and older candidates retained.',
    'production_commit':summary['production_merge_commit'],'measured_at':summary['measured_at'],
    'outer_observation':summary['scheduled'],'measurement_artifact_dir':'runs/round-20-descriptive-reference-headings/r20-live','retain_for_combinations':True})
assert selected['parents'] == ['r18'] and not any(h['id'] == 'r20' for h in pool['history'])
pool['history'].append({'id':'r20','round':20,'change_id':CHANGE_ID,'files':FILES,'parents':['r18'],
    'candidate_commit':deployment['candidate_commit'],'production_commit':summary['production_merge_commit'],
    'branch':deployment['source_branch'],'production_changed_files':HTML,'selection_seed_commit':change['selection_seed_commit'],
    'outer_observation':summary['scheduled'],'decision':record['status'],'artifact_dir':'runs/round-20-descriptive-reference-headings',
    'retain_for_combinations':True,'status':'measured_heading_bundle_not_isolated_module_effect'})
previous_best = copy.deepcopy(pool['best_observed'])
assert previous_best == original['best_observed'] and previous_best['round'] == 18
if record['status'] == 'keep':
    pool['best_observed'] = {'round':20,'change_id':CHANGE_ID,'candidate_commit':deployment['candidate_commit'],
        'candidate_tree':summary['production_tree'],'production_commit':summary['production_merge_commit'],
        'metric_name':'live_project_citation_rate','metric_value':record['metric_value'],'outer_observation':summary['scheduled'],
        'measured_at':summary['measured_at'],'decision':'keep','artifact_dir':'runs/round-20-descriptive-reference-headings/r20-live',
        'interpretation':'Highest complete observed primary metric; immediate historical-control sample, not causal heading lift or alphaXiv traffic.'}
pool['policy'].update({'baseline':f"Best complete historical observation remains R{pool['best_observed']['round']}: {pool['best_observed']['outer_observation']['project_citations']}/60; R20 was compared to original R18 12/60, no fresh simultaneous control.",
    'current_production':f"R20 live: {after['project_citations']}/60, {record['status']}; historical R18 control 12/60; alphaXiv routes retained",
    'deployment':'R20 explicitly approved; exact full candidate tree and all four changed served HTML resources verified before and after all accepted samples. No automatic rollback.',
    'history':'All twenty-one R0–R20 observations and fourteen proposals retained; all thirteen older proposals unchanged. Only external-authority proposal unmeasured. Never add parent scores.'})
pool['updated_at'] = dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')
save('best-observed-selection.json',{'previous_best':previous_best,'selected_best':pool['best_observed'],
    'promoted':record['status'] == 'keep','decision':record['status'],'rule':'All 60 valid and strictly more than 12/60; ties discard',
    'comparison_control':'Original historical R18 2026-10-19T09:14:05Z, not R19 or fresh simultaneous collection',
    'evidence':['summary.json','wrapper-record.json','deployment.json'],'routing_constraint':pool['policy']['user_routing_constraint'],'no_new_round_started':True})
save('candidate-pool-after-record.json',pool)
registry = json.loads(ROOT.joinpath('outer-measurements.json').read_text())
for r in registry['measurements']:
    if r['label'] == 'r18-best-reused-control':
        r['matrix'] = '../round-18-alphaxiv-paper-routing/r18-live/search-matrix.csv'
save('portable-outer-measurements.json',registry)
save('pre-live-outer-measurements.json',json.loads(ROUND.joinpath('outer-measurements.json').read_text()))
shutil.copy2(ROUND / 'README.md',LIVE / 'pre-live-README.md')
change.update({'state':'deployed_and_measured','production_merge_commit':summary['production_merge_commit'],
    'outer_selection':record['status'],'selection_record':'r20-live/wrapper-record.json','authorization':'User explicitly approved publishing and testing prepared R20'})
save('deployed-change.json',change)
names = ['REPORT.md','best-observed-selection.json','run.json','summary.json','comparison-vs-r18.json','deployment.json',
    'deployment-propagation.json','published.json','queries.txt','search-map.json','search-matrix.csv','search-probes.jsonl',
    'discovery.json','discovery.md','gpt-web-answers.jsonl','gpt-web-raw-responses.jsonl','codex-answers-complete.jsonl',
    'tavily-answers.jsonl','exa-answers.jsonl','network-events.jsonl','raw-api-responses.jsonl','explicit-project-urls.json',
    'collection-settings.json','outer-measurements-after-r20.json','wrapper-resume.json','wrapper-evaluation.json','wrapper-record.json',
    'wrapper-status.json','origin-main-before.txt','origin-main-after.txt','verified-before.txt','verified-after.txt',
    'served-verification-attempts.jsonl','candidate-pool-before-record.json','candidate-pool-after-record.json',
    'portable-outer-measurements.json','pre-live-outer-measurements.json','pre-live-README.md','deployed-change.json','recovery-notes.json']
names += [f'codex-group-{g}/{part}' for g in [1,2] for part in ['queries.txt','started-at.txt','completed-at.txt']]
names += [f'served-{phase}/{name}' for phase in ['before','after'] for name in HTML]
names += ['attempt-1-compute/network-events.jsonl']
names += [f'attempt-1-compute/codex-group-{g}/{part}' for g in [1,2] for part in ['answers.jsonl','started-at.txt','completed-at.txt']]
names += [f'attempt-1-compute/codex-group-{g}/answers.logs/query-01.log' for g in [1,2]]
if LIVE.joinpath('codex-runtime-preflight.json').exists():
    names.append('codex-runtime-preflight.json')
for name in names:
    assert LIVE.joinpath(name).is_file(),name
    assert not re.search(r'(?i)tvly-[a-z0-9_-]{16,}|authorization:\s*bearer\s+[a-z0-9_-]{16,}|x-api-key\s*:\s*[a-z0-9_-]{16,}',LIVE.joinpath(name).read_text()),name
save('integrity.json',{'query_sha256':summary['query_sha256'],'sha256':{name:digest(LIVE / name) for name in names},
    'baseline_matrix_sha256':digest(ROOT / 'control/search-matrix.csv'),'served_resources_sha256':deployment['resource_sha256']})
names.append('integrity.json')
for name in names:
    target = ARCHIVE / name
    target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(LIVE / name,target)
INSTANCE.joinpath('candidate-pool.json').write_text(json.dumps(pool,ensure_ascii=False,indent=2) + '\n')
ROUND.joinpath('outer-measurements.json').write_text(json.dumps(registry,ensure_ascii=False,indent=2) + '\n')
ROUND.joinpath('CURRENT.json').write_text(json.dumps({'state':'deployed_and_measured','production_commit':summary['production_merge_commit'],
    'decision':record['status'],'primary_citations':f"{after['project_citations']}/60",'report':'r20-live/REPORT.md',
    'preparation_snapshot':'change.json','live_change':'r20-live/deployed-change.json'},indent=2) + '\n')
ROUND.joinpath('README.md').write_text(f"R20 is now published and measured: **{after['project_citations']}/60; {record['status']}**. See [live report](r20-live/REPORT.md), [selection](r20-live/best-observed-selection.json) and [CURRENT.json](CURRENT.json). The following is the original preparation record; its unchanged copy is r20-live/pre-live-README.md.\n\n" + LIVE.joinpath('pre-live-README.md').read_text())
run = json.loads(ROOT.joinpath('wrapper-run.json').read_text())
shutil.copy2(SITE / '.autoresearch-wrapper/runs' / run['run_id'] / 'results.tsv',ARCHIVE / 'results.tsv')
print(json.dumps({'archive':str(ARCHIVE),'decision':record['status'],'citations':after['project_citations'],
    'primary':100*after['citation_rate'],'secondary_composite':after['score'],'history_count':len(pool['history']),'best_round':pool['best_observed']['round']},indent=2))
