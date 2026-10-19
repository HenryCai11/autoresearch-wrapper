"""Append complete R19 evidence and preserve all historical candidates."""
import copy
import datetime as dt
import re
import shutil
from common import *

assert os.environ.get('SLURM_JOB_ID')
LIVE = ROOT / 'r19-live'
ROUND = DEST
ARCHIVE = ROUND / 'r19-live'
assert not ARCHIVE.exists(), 'Append-only live archive refuses overwrite'
summary = json.loads(LIVE.joinpath('summary.json').read_text())
record = json.loads(LIVE.joinpath('wrapper-record.json').read_text())
deployment = json.loads(LIVE.joinpath('deployment.json').read_text())
change = json.loads(ROOT.joinpath('change.json').read_text())
control = json.loads(ROOT.joinpath('control/summary.json').read_text())
validation = json.loads(ROOT.joinpath('validation.json').read_text())
before = summary['matched_valid_comparison']['baseline']
after = summary['matched_valid_comparison']['r19']
assert summary['scheduled']['valid_responses'] == before['n'] == 60
assert before['project_citations'] == 12
assert record['status'] == summary['decision'] == ('keep' if after['project_citations'] > 12 else 'discard')

def write(name, value):
    LIVE.joinpath(name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')

body = f'''# EAU R19 — exact retained shared-entity metadata on R18, live outer measurement

R19 was explicitly approved and published as `{summary['production_merge_commit']}`.
All four changed HTML resources matched the exact candidate before collection
and again after every request had completed. Initial verification:
{deployment['served_version_verified_at']}; final:
{deployment['served_version_reverified_at']}.

## Combination and deployment

R19 replays the final measured R10 JSON-LD blocks on the kept R18 tree.
Each document has one page-specific WebPage and the same canonical
ScholarlyArticle @id, with page mainEntity links to that paper.
Only four schema blocks changed. All non-JSON-LD bytes, bodies, visible text,
titles, headings, result data, alphaXiv reading links, citation/PDF fields,
BibTeX, scripts, styles, machine summaries and crawler files are unchanged.

All {len(validation['checks'])} local structural/factual checks passed.
Visible homepage text remained {validation['visible_home_chars_after']} characters
(limit {validation['limit']}). No inner score or browser/visual test was performed.
One homepage operation used geo-apply; three exact support-page replacements
used apply_patch in the allocated worktree. No wrapper-core change was made.

combination-source.json and parents/ preserve the exact final R10 commit,
original payloads and operation hashes plus inherited R18 routing operations.
Failed initial R10 attempts were not replayed. Reversing these four replacements
recovers R18 exactly. R10's old 6/60 discard against R9 8/60 remains untouched;
no parent score was added, averaged or used to predict this new observation.

An isolated branch on then-current R18 main was patched to the approved
candidate and its entire tree checked before merge. Candidate, deploy and main
merge commits differ, but complete candidate/production trees match.
The first served check found a stale page; no eval searches were issued until
all four resources matched. GPT/API timestamps and both Codex group markers
are bounded by successful before/after served checks.

## Frozen comparison

The control is the preserved complete R18 measurement at
2026-10-19T09:14:05Z, not a fresh simultaneous control. Keep requires all 60
valid and strictly more than 12/60 project-domain citation cells; ties discard.
No memory-model or inner-metric dimension. The copied collection-settings.json
retains legacy R9 baseline wording; the actual control is the registered R18
matrix and fingerprint.

| Engine | R18 citations | R19 citations | R19 valid |
| --- | ---: | ---: | ---: |
'''
for engine,stats in summary['by_engine'].items():
    old = control['by_engine'][engine]
    body += f"| {engine} | {old['project_citations']}/15 | {stats['project_citations']}/15 | {stats['valid_responses']}/15 |\\n"
body += f'''
Primary: **{before['project_citations']}/60 → {after['project_citations']}/60**
({100*before['citation_rate']:.2f}% → {100*after['citation_rate']:.2f}%).
Secondary legacy composite, report-only: {before['score']:.2f} → {after['score']:.2f}.
Citation cells gained/lost: {len(summary['citation_transitions']['gained'])}/{len(summary['citation_transitions']['lost'])}.
Explicit project URL cells: {summary['explicit_project_url_cells']}/60.
Explicit support-page URL cells: {summary['explicit_support_page_url_cells']}/60.
Wrapper decision: **{record['status']}**.

The unchanged judge includes bare project-domain occurrences; these are not
necessarily explicit source links. See rank/url and explicit-project-urls.json.
alphaXiv and arXiv are not the project domain. These tool results are not
consumer chat-app results, and no alphaXiv clicks/visits were measured.

## Selection and retained history

This is one immediate sample against historical R18, not an isolated causal
estimate of shared identity or its interaction with the other modules.
Search variation, recrawl delays and stale indexing remain possible.
Selection and publication are separate: R19 remains live without automatic
rollback. All alphaXiv reading routes remain required in future candidates.

All twenty R0–R19 observations and thirteen proposals are retained, with all
twelve older proposals unchanged. R10 remains available as its original measured
discard, and R19 is separately identified with parents R18/R10 regardless of
this new keep/discard decision. Only the external-authority proposal remains
unmeasured; its backlink state is unknown and no external page was edited.
No candidate deletion, pruning, next round or follow-up schedule was performed.
'''
LIVE.joinpath('REPORT.md').write_text(body)
raw = []
for provider in ['tavily', 'exa']:
    for i in range(1, 16):
        raw.append({'provider': provider, 'query_index': i,
            'request': json.loads(LIVE.joinpath(f'{provider}-raw/{i:02d}-request.json').read_text()),
            'response': json.loads(LIVE.joinpath(f'{provider}-raw/{i:02d}.json').read_text())})
LIVE.joinpath('raw-api-responses.jsonl').write_text(''.join(json.dumps(row, ensure_ascii=False) + '\n' for row in raw))

pool_path = INSTANCE / 'candidate-pool.json'
pool = json.loads(pool_path.read_text())
original = json.loads(ROOT.joinpath('candidate-pool-before.json').read_text())
assert pool['current_round'] == 19 and pool['selected_candidate_id'] == SELECTED
assert pool['history'] == original['history'] and len(pool['proposals']) == 13
assert all(p in pool['proposals'] for p in original['proposals'])
write('candidate-pool-before-record.json', pool)
selected = next(p for p in pool['proposals'] if p['id'] == SELECTED)
selected.update({'status': record['status'], 'measured': True, 'deployment_status': 'live',
    'interpretation': 'Measured exact R10 metadata on R18 as a separate combination; historical control, not an isolated causal module effect. Preserve alphaXiv routes and original candidates.',
    'production_commit': summary['production_merge_commit'], 'measured_at': summary['measured_at'],
    'outer_observation': summary['scheduled'], 'measurement_artifact_dir': 'runs/round-19-shared-entity-combination/r19-live',
    'retain_for_combinations': True})
assert not any(p['id'] == 'r19' for p in pool['history'])
pool['history'].append({'id': 'r19', 'round': 19, 'change_id': CHANGE_ID,
    'files': change['files'], 'parents': change['parents'], 'candidate_commit': deployment['candidate_commit'],
    'production_commit': summary['production_merge_commit'], 'branch': deployment['source_branch'],
    'production_changed_files': change['production_changed_files'], 'selection_seed_commit': change['selection_seed_commit'],
    'outer_observation': summary['scheduled'], 'decision': record['status'],
    'artifact_dir': 'runs/round-19-shared-entity-combination', 'retain_for_combinations': True,
    'status': 'measured_combination_not_isolated_module_effect'})
previous_best = copy.deepcopy(pool['best_observed'])
assert previous_best == original['best_observed'] and previous_best['round'] == 18
if record['status'] == 'keep':
    pool['best_observed'] = {'round': 19, 'change_id': CHANGE_ID, 'candidate_commit': deployment['candidate_commit'],
        'candidate_tree': summary['production_tree'], 'production_commit': summary['production_merge_commit'],
        'metric_name': 'live_project_citation_rate', 'metric_value': record['metric_value'],
        'outer_observation': summary['scheduled'], 'measured_at': summary['measured_at'], 'decision': 'keep',
        'artifact_dir': 'runs/round-19-shared-entity-combination/r19-live',
        'interpretation': 'Highest complete observed primary metric; immediate historical-control sample, not causal lift or alphaXiv traffic.'}
    pool['policy']['baseline'] = f"R19 used historical R18 12/60. New best complete observation: R19 {after['project_citations']}/60; exact tree retains the user-required alphaXiv routes. No simultaneous control."
else:
    pool['policy']['baseline'] = 'R18 remains highest complete historical primary observation, 12/60 and composite 35.19444. R19 remains live with required alphaXiv routes; do not restore arXiv reading buttons when preparing a future candidate.'
pool['policy']['current_production'] = f"R19 live: {after['project_citations']}/60, {record['status']}; compared with historical R18 12/60; alphaXiv reading routes retained"
pool['policy']['deployment'] = 'R19 explicitly approved; exact complete candidate tree and all four served changed files verified before and after the completed 60-cell collection. No rollback.'
pool['policy']['history'] = 'All twenty R0–R19 observations and thirteen proposals retained; all twelve older proposals unchanged. Only the external-authority proposal remains unmeasured. Never add parent scores.'
pool['policy']['user_routing_constraint'] = 'Preserve https://www.alphaxiv.org/abs/2610.16523 for paper-reading entry points in future candidates, independently of project-domain GEO selection. Scholarly arXiv identifiers/PDF/BibTeX remain unchanged.'
pool['updated_at'] = dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')
write('best-observed-selection.json', {'previous_best': previous_best, 'selected_best': pool['best_observed'],
    'promoted': record['status'] == 'keep', 'decision': record['status'],
    'rule': 'All 60 valid and strictly more than 12/60 project-domain citation cells; ties discard.',
    'comparison_control': 'Historical R18, 2026-10-19T09:14:05Z, not fresh simultaneous collection',
    'evidence': ['summary.json', 'wrapper-record.json', 'deployment.json'],
    'routing_constraint': pool['policy']['user_routing_constraint'], 'no_new_round_started': True})
write('candidate-pool-after-record.json', pool)

registry = json.loads(ROOT.joinpath('outer-measurements.json').read_text())
for measurement in registry['measurements']:
    if measurement['label'] == 'r18-best-reused-control':
        measurement['matrix'] = '../round-18-alphaxiv-paper-routing/r18-live/search-matrix.csv'
write('portable-outer-measurements.json', registry)
write('pre-live-outer-measurements.json', json.loads(ROUND.joinpath('outer-measurements.json').read_text()))
shutil.copy2(ROUND / 'README.md', LIVE / 'pre-live-README.md')
change.update({'state': 'deployed_and_measured', 'production_merge_commit': summary['production_merge_commit'],
    'outer_selection': record['status'], 'selection_record': 'r19-live/wrapper-record.json',
    'authorization': 'User explicitly approved publishing R19 and measuring it.'})
write('deployed-change.json', change)
integrity_names = ['gpt-web-answers.jsonl', 'codex-answers-complete.jsonl', 'tavily-answers.jsonl',
    'exa-answers.jsonl', 'search-matrix.csv', 'search-map.json', 'raw-api-responses.jsonl',
    'network-events.jsonl', 'deployment.json', 'deployment-propagation.json', 'recording-attempt-1.txt', 'record-deployment-before-branch-label-fix.py', 'collection-settings.json', 'queries.txt',
    'best-observed-selection.json', 'candidate-pool-before-record.json', 'candidate-pool-after-record.json',
    'codex-group-1/started-at.txt', 'codex-group-1/completed-at.txt', 'codex-group-2/started-at.txt', 'codex-group-2/completed-at.txt']
write('integrity.json', {'query_sha256': summary['query_sha256'],
    'sha256': {name: digest(LIVE / name) for name in integrity_names},
    'baseline_matrix_sha256': digest(ROOT / 'control/search-matrix.csv'),
    'served_resources_sha256': deployment['resource_sha256']})
names = ['REPORT.md', 'best-observed-selection.json', 'run.json', 'summary.json', 'comparison-vs-r18.json',
    'deployment.json', 'deployment-propagation.json', 'recording-attempt-1.txt', 'record-deployment-before-branch-label-fix.py', 'queries.txt', 'search-map.json', 'search-matrix.csv', 'search-probes.jsonl',
    'discovery.json', 'discovery.md', 'gpt-web-answers.jsonl', 'codex-answers-complete.jsonl',
    'tavily-answers.jsonl', 'exa-answers.jsonl', 'network-events.jsonl', 'raw-api-responses.jsonl',
    'explicit-project-urls.json', 'collection-settings.json', 'outer-measurements-after-r19.json',
    'wrapper-resume.json', 'wrapper-evaluation.json', 'wrapper-record.json', 'wrapper-status.json',
    'origin-main-before.txt', 'origin-main-after.txt', 'verified-before.txt', 'verified-after.txt',
    'candidate-pool-before-record.json', 'candidate-pool-after-record.json', 'portable-outer-measurements.json',
    'pre-live-outer-measurements.json', 'pre-live-README.md', 'deployed-change.json', 'integrity.json']
names += [f'codex-group-{g}/{part}' for g in [1, 2] for part in ['started-at.txt', 'completed-at.txt']]
names += [f'served-{phase}/{name}' for phase in ['before', 'after'] for name in FILES]
for name in names:
    assert LIVE.joinpath(name).is_file(), name
    assert not re.search(r'(?i)tvly-|authorization:\s*bearer|x-api-key\s*:', LIVE.joinpath(name).read_text()), name
for name in names:
    target = ARCHIVE / name
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(LIVE / name, target)
pool_path.write_text(json.dumps(pool, ensure_ascii=False, indent=2) + '\n')
ROUND.joinpath('outer-measurements.json').write_text(json.dumps(registry, ensure_ascii=False, indent=2) + '\n')
ROUND.joinpath('CURRENT.json').write_text(json.dumps({'state': 'deployed_and_measured',
    'production_commit': summary['production_merge_commit'], 'decision': record['status'],
    'primary_citations': f"{after['project_citations']}/60", 'report': 'r19-live/REPORT.md',
    'preparation_snapshot': 'change.json', 'live_change': 'r19-live/deployed-change.json'}, indent=2) + '\n')
run = json.loads(ROOT.joinpath('wrapper-run.json').read_text())
shutil.copy2(SITE / '.autoresearch-wrapper/runs' / run['run_id'] / 'results.tsv', ARCHIVE / 'results.tsv')
print(json.dumps({'archive': str(ARCHIVE), 'selection': record['status'], 'citations': after['project_citations'],
    'composite': after['score'], 'history_count': len(pool['history']), 'proposals': len(pool['proposals'])}, indent=2))
