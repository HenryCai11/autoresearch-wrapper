"""Append measured R17 evidence while using the R16 9/60 selection threshold."""
import datetime as dt
import hashlib
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LIVE = ROOT / 'r17-live'
INSTANCE = Path('/project/aip-xiye17/henrycai/autoresearch-wrapper/geo/instances/eau')
ROUND = INSTANCE / 'runs/round-17-descriptive-heading-static-method'
DEST = ROUND / 'r17-live'
summary = json.loads(LIVE.joinpath('summary.json').read_text())
record = json.loads(LIVE.joinpath('wrapper-record.json').read_text())
deployment = json.loads(LIVE.joinpath('deployment.json').read_text())
change = json.loads(ROOT.joinpath('change.json').read_text())
control = json.loads(ROOT.joinpath('control/summary.json').read_text())
before = summary['matched_valid_comparison']['baseline']
after = summary['matched_valid_comparison']['r17']
assert summary['scheduled']['valid_responses'] == before['n'] == 60
assert record['status'] == summary['decision']


def write(name, value):
    LIVE.joinpath(name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


body = f'''# EAU R17 — descriptive headings with static method reference, live outer measurement

R17 was approved, merged and published as `{summary['production_merge_commit']}`.
The changed homepage byte-matched the exact candidate before and after collection.
Verification began at {deployment['served_version_verified_at']}.

On the best measured R16 heading seed, one exact archived R13 operation inserts
persistent environment/agent explanations and all six knob labels. Its text is
copied verbatim from existing script.js data; the default user description is
not duplicated. Both R16 H2s, interactive explorer, result evidence, all other
sections/pages, metadata, scripts and styles remain unchanged. No R12 H1 or R14
second-backbone table is inherited. All 31 local structural/factual checks
passed; visible homepage text changed 5433 → 6086 characters (limit 9000).
No browser/visual test was performed; rendered fit and behavior are unverified.

combination-source.json and parents/ retain the original R13/R16 operation hashes
and commit/tree IDs. Removing the method insertion recovers R16 exactly; reversing
only the R16 headings recovers the original R13 HTML exactly. This is a separate
combination candidate, not an edit to either original measured proposal. An
isolated branch based on R16 was patched to the exact candidate and its whole
tree verified before merging. Candidate, deploy and production merge commits
are distinct, with identical candidate and production file trees. The final
served check required all 60 valid responses and both Codex completion markers;
request timestamps were checked against the before/after served checks.

The decision metric remains the frozen four-engine project-domain citation rate.
Inner scores were not computed. The R16 control is the preserved live 60-cell
measurement completed at 2026-10-18T06:31:55Z, not a fresh simultaneous control.
The threshold is strictly above R16's 9/60, not the former R9 8/60 threshold.

| Engine | R16 citations | R17 citations | R17 valid responses |
| --- | ---: | ---: | ---: |
'''
for engine, stats in summary['by_engine'].items():
    old = control['by_engine'][engine]
    body += f"| {engine} | {old['project_citations']}/15 | {stats['project_citations']}/15 | {stats['valid_responses']}/15 |\n"
body += f'''
Primary: **{before['project_citations']}/60 → {after['project_citations']}/60**
({100*before['citation_rate']:.2f}% → {100*after['citation_rate']:.2f}%).
Legacy outer composite: {before['score']:.2f} → {after['score']:.2f}.
Citation cells gained/lost: {len(summary['citation_transitions']['gained'])}/{len(summary['citation_transitions']['lost'])}.
Explicit project URL cells: {summary['explicit_project_url_cells']}/60.
Explicit support-page URL cells: {summary['explicit_support_page_url_cells']}/60.
Wrapper decision: **{record['status']}** (strict improvement in the primary required).

The existing judge counts bare project-domain occurrences as citations. These
are not necessarily explicit source links; inspect `rank`, `url`, and
`explicit-project-urls.json`. Tool responses are not consumer chat-app results.

This is one immediate post-deployment sample of the candidate, not an isolated
causal estimate of the static method block or its interaction with headings. Indexes may still contain older pages and
search results vary; the historical control does not isolate causal contribution.
No later follow-up has been scheduled. Selection and deployment are separate:
R17 remains live; no post-measurement rollback, candidate deletion or pruning was
performed. The individual R13 and different R15 bundle observations are retained
as history, not treated as isolated module effects or added to R16's 9/60.

The maintained instance candidate ledger now records this observation and keeps
the candidate available for later combinations regardless of keep/discard.
All prior observations and exact archived candidate operations remain retained;
none of their scores was added or averaged to predict R17. Only the external-authority proposal
remains unmeasured, with backlink state unknown and separate authority required.
'''
LIVE.joinpath('REPORT.md').write_text(body)
raw = []
for provider in ['tavily', 'exa']:
    for i in range(1, 16):
        raw.append({'provider': provider, 'query_index': i,
                    'request': json.loads(LIVE.joinpath(f'{provider}-raw/{i:02d}-request.json').read_text()),
                    'response': json.loads(LIVE.joinpath(f'{provider}-raw/{i:02d}.json').read_text())})
LIVE.joinpath('raw-api-responses.jsonl').write_text(''.join(json.dumps(row, ensure_ascii=False) + '\n' for row in raw))

# Preserve both the original preparation snapshot and the ledger current at record time.
pool_path = INSTANCE / 'candidate-pool.json'
pool = json.loads(pool_path.read_text())
write('candidate-pool-before-record.json', pool)
selected = next(item for item in pool['proposals'] if item['id'] == 'descriptive-heading-static-method')
selected.update({'status': record['status'], 'measured': True, 'deployment_status': 'live',
                 'interpretation': 'Measured immediate post-deployment observation against preserved R16; not an isolated causal module effect. Retain for future combinations.',
                 'production_commit': summary['production_merge_commit'],
                 'measured_at': summary['measured_at'], 'outer_observation': summary['scheduled'],
                 'measurement_artifact_dir': 'runs/round-17-descriptive-heading-static-method/r17-live',
                 'retain_for_combinations': True})
assert not any(item['id'] == 'r17' for item in pool['history']), 'Do not append the R17 observation twice'
pool['history'].append({'id': 'r17', 'round': 17, 'change_id': 'r17-descriptive-heading-static-method',
    'files': change['files'], 'parents': change['parents'], 'candidate_commit': deployment['candidate_commit'],
    'production_commit': summary['production_merge_commit'], 'branch': deployment['source_branch'],
    'production_changed_files': change['production_changed_files'], 'selection_seed_commit': change['selection_seed_commit'],
    'outer_observation': summary['scheduled'], 'decision': record['status'],
    'artifact_dir': 'runs/round-17-descriptive-heading-static-method', 'retain_for_combinations': True,
    'status': 'measured_bundle_not_isolated_module_effect'})
pool['policy']['current_production'] = f"R17 live: {after['project_citations']}/60, {record['status']}; this comparison uses preserved R16 9/60"
pool['policy']['deployment'] = 'R17 publication was explicitly approved; exact candidate tree and before/after served bytes verified for the completed real 60-cell collection.'
pool['policy']['history'] = 'All 18 R0–R17 observations and all eleven proposals retained; all ten old proposals unchanged. The new combination has its own measurement; only the external-authority proposal is unmeasured. Do not add parent scores.'
previous_best = json.loads(json.dumps(pool['best_observed']))
assert previous_best['round'] == 16 and previous_best['outer_observation']['project_citations'] == 9
if record['status'] == 'keep':
    pool['best_observed'] = {'round': 17, 'change_id': summary['change_id'],
        'candidate_commit': deployment['candidate_commit'], 'candidate_tree': summary['production_tree'],
        'production_commit': summary['production_merge_commit'], 'metric_name': 'live_project_citation_rate',
        'metric_value': record['metric_value'], 'outer_observation': summary['scheduled'],
        'measured_at': summary['measured_at'], 'decision': 'keep',
        'artifact_dir': 'runs/round-17-descriptive-heading-static-method/r17-live',
        'interpretation': 'Highest complete observed candidate under the locked primary metric; immediate historical-control comparison, not causal lift.'}
    pool['policy']['baseline'] = f"R17 used historical R16 9/60. New best complete observation: R17 {after['project_citations']}/60; use its exact tree as the next selection seed. No simultaneous control collected."
else:
    assert record['status'] == 'discard'
    pool['policy']['baseline'] = 'R16 remains the best complete observed candidate at 9/60, composite 31.86111, and the next selection seed. R17 was compared with its historical measurement.'
write('best-observed-selection.json', {'previous_best': previous_best, 'selected_best': pool['best_observed'],
    'promoted': record['status'] == 'keep', 'decision': record['status'],
    'rule': 'All 60 valid and strictly more than 9/60 project-domain citation cells; ties discard.',
    'comparison_control': 'Historical R16, 2026-10-18T06:31:55Z, not a fresh simultaneous collection',
    'evidence': ['summary.json', 'wrapper-record.json', 'deployment.json'],
    'no_new_round_started': True})
pool['updated_at'] = dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')
write('candidate-pool-after-record.json', pool)

registry = json.loads(ROOT.joinpath('outer-measurements.json').read_text())
for measurement in registry['measurements']:
    if measurement['label'] == 'r16-best-reused-control':
        measurement['matrix'] = '../round-16-descriptive-section-headings/r16-live/search-matrix.csv'
write('portable-outer-measurements.json', registry)
write('pre-live-outer-measurements.json', json.loads(ROUND.joinpath('outer-measurements.json').read_text()))
shutil.copy2(ROUND / 'README.md', LIVE / 'pre-live-README.md')
change.update({'state': 'deployed_and_measured', 'production_merge_commit': summary['production_merge_commit'],
               'outer_selection': record['status'], 'selection_record': 'r17-live/wrapper-record.json',
               'authorization': 'User explicitly approved publishing R17 and measuring it.'})
write('deployed-change.json', change)
write('integrity.json', {'query_sha256': summary['query_sha256'],
    'sha256': {name: digest(LIVE / name) for name in ['gpt-web-answers.jsonl', 'codex-answers-complete.jsonl',
        'tavily-answers.jsonl', 'exa-answers.jsonl', 'search-matrix.csv', 'search-map.json', 'raw-api-responses.jsonl',
        'network-events.jsonl', 'deployment.json', 'collection-settings.json', 'queries.txt',
        'best-observed-selection.json', 'candidate-pool-before-record.json', 'candidate-pool-after-record.json',
        'codex-group-1/started-at.txt', 'codex-group-1/completed-at.txt',
        'codex-group-2/started-at.txt', 'codex-group-2/completed-at.txt']},
    'baseline_matrix_sha256': digest(ROOT / 'control/search-matrix.csv'),
    'served_resources_sha256': deployment['resource_sha256']})
names = ['REPORT.md', 'best-observed-selection.json', 'run.json', 'summary.json', 'comparison-vs-r16.json', 'deployment.json',
         'queries.txt', 'search-map.json', 'search-matrix.csv', 'search-probes.jsonl', 'discovery.json', 'discovery.md',
         'gpt-web-answers.jsonl', 'codex-answers-complete.jsonl', 'tavily-answers.jsonl', 'exa-answers.jsonl',
         'network-events.jsonl', 'raw-api-responses.jsonl', 'explicit-project-urls.json', 'collection-settings.json',
         'outer-measurements-after-r17.json', 'wrapper-resume.json', 'wrapper-evaluation.json',
         'wrapper-record.json', 'wrapper-status.json', 'origin-main-before.txt', 'origin-main-after.txt',
         'verified-before.txt', 'verified-after.txt', 'codex-group-1/started-at.txt', 'codex-group-1/completed-at.txt', 'codex-group-2/started-at.txt', 'codex-group-2/completed-at.txt', 'candidate-pool-before-record.json', 'candidate-pool-after-record.json',
         'portable-outer-measurements.json', 'pre-live-outer-measurements.json', 'pre-live-README.md', 'deployed-change.json', 'integrity.json']
for phase in ['before', 'after']:
    names += [f'served-{phase}/{name}' for name in change['production_changed_files']]
assert not DEST.exists(), 'Append-only live archive refuses overwrite'
for name in names:
    source = LIVE / name
    assert source.is_file(), source
    assert not re.search(r'(?i)tvly-|authorization:\s*bearer|x-api-key\s*:', source.read_text()), source.name
for name in names:
    target = DEST / name
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(LIVE / name, target)

# Update generated current-state data only after the evidence archive is complete.
pool_path.write_text(json.dumps(pool, ensure_ascii=False, indent=2) + '\n')
ROUND.joinpath('outer-measurements.json').write_text(json.dumps(registry, ensure_ascii=False, indent=2) + '\n')
ROUND.joinpath('CURRENT.json').write_text(json.dumps({'state': 'deployed_and_measured',
    'production_commit': summary['production_merge_commit'], 'decision': record['status'],
    'primary_citations': f"{after['project_citations']}/60", 'report': 'r17-live/REPORT.md',
    'preparation_snapshot': 'change.json', 'live_change': 'r17-live/deployed-change.json'}, indent=2) + '\n')
run = json.loads(ROOT.joinpath('wrapper-run.json').read_text())
run_dir = Path('/scratch/henrycai/eau-r17-20261018/.autoresearch-wrapper/runs') / run['run_id']
shutil.copy2(run_dir / 'results.tsv', DEST / 'results.tsv')
print(json.dumps({'archive': str(DEST), 'selection': record['status'], 'citations': after['project_citations'],
                  'composite': after['score'], 'ledger_history_count': len(pool['history']),
                  'queued_proposals_preserved': len(pool['proposals'])}, indent=2))
