"""Append complete R18 evidence and preserve all historical candidates."""
import copy
import datetime as dt
import re
import shutil
from common import *

assert os.environ.get('SLURM_JOB_ID')
LIVE = ROOT / 'r18-live'
ROUND = DEST
ARCHIVE = ROUND / 'r18-live'
assert not ARCHIVE.exists(), 'Append-only live archive refuses overwrite'
summary = json.loads(LIVE.joinpath('summary.json').read_text())
record = json.loads(LIVE.joinpath('wrapper-record.json').read_text())
deployment = json.loads(LIVE.joinpath('deployment.json').read_text())
change = json.loads(ROOT.joinpath('change.json').read_text())
control = json.loads(ROOT.joinpath('control/summary.json').read_text())
validation = json.loads(ROOT.joinpath('validation.json').read_text())
before = summary['matched_valid_comparison']['baseline']
after = summary['matched_valid_comparison']['r18']
assert summary['scheduled']['valid_responses'] == before['n'] == 60
assert before['project_citations'] == 10
assert record['status'] == summary['decision'] == ('keep' if after['project_citations'] > 10 else 'discard')

def write(name, value):
    LIVE.joinpath(name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')

body = f'''# EAU R18 — alphaXiv paper-reading routes, live outer measurement

R18 was explicitly approved, merged and published as `{summary['production_merge_commit']}`.
All seven changed served files byte-matched the candidate before and after every
search request. Initial verification: {deployment['served_version_verified_at']}.
Final verification: {deployment['served_version_reverified_at']}.

## Intervention and validation

This user-requested routing bundle changes exactly nine URL/label occurrences
in seven files on the best observed R17 tree. The six static HTML paper-reading
anchors, README/llms.txt Paper entries and site-config.js paperUrl now point to
https://www.alphaxiv.org/abs/2610.16523. The public target's title, canonical URL
and arXiv identifier were verified independently during preparation.

arXiv identifiers, PDF metadata, all HTML heads and JSON-LD identity, CITATION.cff
and both BibTeX blocks are unchanged. All factual claims, the R17 persistent
method reference, R16 headings, R9 result evidence, project-site self-links,
script.js, styles, assets and crawler files remain unchanged.
All {len(validation['checks'])} local structural/factual checks passed; visible homepage
text changed {validation['visible_home_chars_before']} → {validation['visible_home_chars_after']}
characters (limit {validation['limit']}). No inner score or browser/visual test was performed.

Five replacements used the existing graph-supported file nodes; four support-file
replacements used apply_patch in the allocated worktree. The full operation
manifest and both subsets are preserved. No wrapper-core extension was made.
Candidate, isolated deploy and main merge commits differ, but complete candidate
and production trees match. Request timestamps and both Codex completion markers
are bounded by the served checks, which include all seven changed resources.

## Frozen four-engine comparison

The control is the preserved R17 60-cell observation at 2026-10-18T15:48:02Z,
not a fresh simultaneous control. Keep requires strictly more than 10/60 with
all 60 responses valid; ties discard. No memory-model or inner-metric dimension.
The copied collection-settings.json retains historical R9 baseline wording;
the actual registered control is R17, as shown in the matrix fingerprint,
outer-measurements.json, deployment record and this report.

| Engine | R17 citations | R18 citations | R18 valid responses |
| --- | ---: | ---: | ---: |
'''
for engine, stats in summary['by_engine'].items():
    old = control['by_engine'][engine]
    body += f"| {engine} | {old['project_citations']}/15 | {stats['project_citations']}/15 | {stats['valid_responses']}/15 |\n"
body += f'''
Primary: **{before['project_citations']}/60 → {after['project_citations']}/60**
({100*before['citation_rate']:.2f}% → {100*after['citation_rate']:.2f}%).
Legacy outer composite, report-only: {before['score']:.2f} → {after['score']:.2f}.
Citation cells gained/lost: {len(summary['citation_transitions']['gained'])}/{len(summary['citation_transitions']['lost'])}.
Explicit project URL cells: {summary['explicit_project_url_cells']}/60.
Explicit support-page URL cells: {summary['explicit_support_page_url_cells']}/60.
Wrapper decision: **{record['status']}**.

The existing judge also counts bare project-domain occurrences as citations;
those are not necessarily explicit source links. Inspect rank/url and
explicit-project-urls.json separately. alphaXiv and arXiv URLs are not counted
as project-domain citations. Tool responses are not consumer chat-app results.

## Traffic goal, selection and limitations

alphaXiv clicks and visits are **not measured**. Routing future paper clicks to
alphaXiv is the requested behavior, not evidence of a traffic increase.
The matrix measures project-site discovery only; it does not score that traffic
goal. This is one immediate sample against a historical control, not an isolated
causal estimate of routing. Stale indexes, time and search variation may matter.

Selection and publication remain separate: R18 stays live, including the user's
alphaXiv routing request, regardless of this metric decision. No automatic
rollback, candidate deletion, branch pruning, next round or follow-up schedule
was performed. Future candidate preparation must preserve the user's alphaXiv
reading destinations; an older best_observed entry is not permission to restore
arXiv reading buttons. All nineteen R0–R18 observations and twelve proposals
remain available for later combinations, without adding their old scores.
Only the external-authority proposal remains unmeasured; external backlink
state stays unknown, and no external page was edited.
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
assert pool['current_round'] == 18 and pool['selected_candidate_id'] == SELECTED
assert pool['history'] == original['history'] and len(pool['proposals']) == 12
assert all(p in pool['proposals'] for p in original['proposals'])
write('candidate-pool-before-record.json', pool)
selected = next(p for p in pool['proposals'] if p['id'] == SELECTED)
selected.update({'status': record['status'], 'measured': True, 'deployment_status': 'live',
    'interpretation': 'Measured immediate project-domain discovery observation against historical R17; alphaXiv traffic unmeasured. Retain user-requested routing and preserve candidate for combinations.',
    'production_commit': summary['production_merge_commit'], 'measured_at': summary['measured_at'],
    'outer_observation': summary['scheduled'], 'measurement_artifact_dir': 'runs/round-18-alphaxiv-paper-routing/r18-live',
    'retain_for_combinations': True})
assert not any(p['id'] == 'r18' for p in pool['history'])
pool['history'].append({'id': 'r18', 'round': 18, 'change_id': CHANGE_ID,
    'files': change['files'], 'parents': change['parents'], 'candidate_commit': deployment['candidate_commit'],
    'production_commit': summary['production_merge_commit'], 'branch': deployment['source_branch'],
    'production_changed_files': change['production_changed_files'], 'selection_seed_commit': change['selection_seed_commit'],
    'outer_observation': summary['scheduled'], 'decision': record['status'],
    'artifact_dir': 'runs/round-18-alphaxiv-paper-routing', 'retain_for_combinations': True,
    'status': 'measured_routing_bundle_not_isolated_causal_effect'})
previous_best = copy.deepcopy(pool['best_observed'])
assert previous_best == original['best_observed'] and previous_best['round'] == 17
if record['status'] == 'keep':
    pool['best_observed'] = {'round': 18, 'change_id': CHANGE_ID, 'candidate_commit': deployment['candidate_commit'],
        'candidate_tree': summary['production_tree'], 'production_commit': summary['production_merge_commit'],
        'metric_name': 'live_project_citation_rate', 'metric_value': record['metric_value'],
        'outer_observation': summary['scheduled'], 'measured_at': summary['measured_at'], 'decision': 'keep',
        'artifact_dir': 'runs/round-18-alphaxiv-paper-routing/r18-live',
        'interpretation': 'Highest complete observed primary metric; immediate historical-control sample, not causal lift or alphaXiv traffic.'}
    pool['policy']['baseline'] = f"R18 used historical R17 10/60. New best complete observation: R18 {after['project_citations']}/60; exact tree retains the user-required alphaXiv routes. No simultaneous control."
else:
    pool['policy']['baseline'] = 'R17 remains highest complete historical primary observation, 10/60 and composite 34.30556. R18 remains live with required alphaXiv routes; do not restore arXiv reading buttons when preparing a future candidate.'
pool['policy']['current_production'] = f"R18 live: {after['project_citations']}/60, {record['status']}; compared with historical R17 10/60; alphaXiv reading routes retained"
pool['policy']['deployment'] = 'R18 explicitly approved; exact complete candidate tree and all seven served changed files verified before and after the completed 60-cell collection. No rollback.'
pool['policy']['history'] = 'All nineteen R0–R18 observations and twelve proposals retained; all eleven older proposals unchanged. Only the external-authority proposal remains unmeasured. Never add parent scores.'
pool['policy']['user_routing_constraint'] = 'Preserve https://www.alphaxiv.org/abs/2610.16523 for paper-reading entry points in future candidates, independently of project-domain GEO selection. Scholarly arXiv identifiers/PDF/BibTeX remain unchanged.'
pool['updated_at'] = dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')
write('best-observed-selection.json', {'previous_best': previous_best, 'selected_best': pool['best_observed'],
    'promoted': record['status'] == 'keep', 'decision': record['status'],
    'rule': 'All 60 valid and strictly more than 10/60 project-domain citation cells; ties discard.',
    'comparison_control': 'Historical R17, 2026-10-18T15:48:02Z, not fresh simultaneous collection',
    'evidence': ['summary.json', 'wrapper-record.json', 'deployment.json'],
    'routing_constraint': pool['policy']['user_routing_constraint'], 'no_new_round_started': True})
write('candidate-pool-after-record.json', pool)

registry = json.loads(ROOT.joinpath('outer-measurements.json').read_text())
for measurement in registry['measurements']:
    if measurement['label'] == 'r17-best-reused-control':
        measurement['matrix'] = '../round-17-descriptive-heading-static-method/r17-live/search-matrix.csv'
write('portable-outer-measurements.json', registry)
write('pre-live-outer-measurements.json', json.loads(ROUND.joinpath('outer-measurements.json').read_text()))
shutil.copy2(ROUND / 'README.md', LIVE / 'pre-live-README.md')
change.update({'state': 'deployed_and_measured', 'production_merge_commit': summary['production_merge_commit'],
    'outer_selection': record['status'], 'selection_record': 'r18-live/wrapper-record.json',
    'authorization': 'User explicitly approved publishing R18 and measuring it.'})
write('deployed-change.json', change)
integrity_names = ['gpt-web-answers.jsonl', 'codex-answers-complete.jsonl', 'tavily-answers.jsonl',
    'exa-answers.jsonl', 'search-matrix.csv', 'search-map.json', 'raw-api-responses.jsonl',
    'network-events.jsonl', 'deployment.json', 'collection-settings.json', 'queries.txt',
    'best-observed-selection.json', 'candidate-pool-before-record.json', 'candidate-pool-after-record.json',
    'codex-group-1/started-at.txt', 'codex-group-1/completed-at.txt', 'codex-group-2/started-at.txt', 'codex-group-2/completed-at.txt']
write('integrity.json', {'query_sha256': summary['query_sha256'],
    'sha256': {name: digest(LIVE / name) for name in integrity_names},
    'baseline_matrix_sha256': digest(ROOT / 'control/search-matrix.csv'),
    'served_resources_sha256': deployment['resource_sha256']})
names = ['REPORT.md', 'best-observed-selection.json', 'run.json', 'summary.json', 'comparison-vs-r17.json',
    'deployment.json', 'queries.txt', 'search-map.json', 'search-matrix.csv', 'search-probes.jsonl',
    'discovery.json', 'discovery.md', 'gpt-web-answers.jsonl', 'codex-answers-complete.jsonl',
    'tavily-answers.jsonl', 'exa-answers.jsonl', 'network-events.jsonl', 'raw-api-responses.jsonl',
    'explicit-project-urls.json', 'collection-settings.json', 'outer-measurements-after-r18.json',
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
    'primary_citations': f"{after['project_citations']}/60", 'report': 'r18-live/REPORT.md',
    'preparation_snapshot': 'change.json', 'live_change': 'r18-live/deployed-change.json'}, indent=2) + '\n')
run = json.loads(ROOT.joinpath('wrapper-run.json').read_text())
shutil.copy2(SITE / '.autoresearch-wrapper/runs' / run['run_id'] / 'results.tsv', ARCHIVE / 'results.tsv')
print(json.dumps({'archive': str(ARCHIVE), 'selection': record['status'], 'citations': after['project_citations'],
    'composite': after['score'], 'history_count': len(pool['history']), 'proposals': len(pool['proposals'])}, indent=2))
