"""Append measured R14 evidence while keeping the R9 selection threshold."""
import datetime as dt
import hashlib
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LIVE = ROOT / 'r14-live'
INSTANCE = Path('/project/aip-xiye17/henrycai/autoresearch-wrapper/geo/instances/eau')
ROUND = INSTANCE / 'runs/round-14-static-second-backbone-evidence'
DEST = ROUND / 'r14-live'
summary = json.loads(LIVE.joinpath('summary.json').read_text())
record = json.loads(LIVE.joinpath('wrapper-record.json').read_text())
deployment = json.loads(LIVE.joinpath('deployment.json').read_text())
change = json.loads(ROOT.joinpath('change.json').read_text())
control = json.loads(ROOT.joinpath('control/summary.json').read_text())
before = summary['matched_valid_comparison']['baseline']
after = summary['matched_valid_comparison']['r14']
assert summary['scheduled']['valid_responses'] == before['n'] == 60
assert record['status'] == summary['decision']


def write(name, value):
    LIVE.joinpath(name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


body = f'''# EAU R14 — static second-backbone evidence, live outer measurement

R14 was approved, merged and published as `{summary['production_merge_commit']}`.
The changed homepage byte-matched the exact candidate before and after collection.
Verification began at {deployment['served_version_verified_at']}.

Relative to the best R9 seed, R14 adds one default-open reference table inside the
existing results section. All nine Qwen2.5-7B-Instruct method rows and 36 values
are copied from existing script.js data at the same three-decimal precision.
The model label and caption distinguish the reference from the unchanged main
Qwen3 charts/table. Original model-switch markup, renderer selectors, metadata,
scripts, styles, links and every other named section remain unchanged. No new
results, relative gains, tau2 numbers or research claims were added. All 27 local
checks passed; no browser or visual test was performed.

R7 overview, R8 routes and R9 default static results are retained. Relative to
previous R13 production, index.html both adds this table and removes R13's
unkept static component reference. An isolated deploy branch based on R13 was
patched to the exact candidate tree and the entire tree verified before merging;
a blind merge of the historical-seed branch would have retained the wrong block.
Candidate, deploy and production merge commits are distinct; candidate and
production file trees are identical in deployment.json. The final served check
was gated on all 60 responses and both Codex completion markers, with collection
timestamps independently validated.

The decision metric remains the frozen four-engine project-domain citation rate.
Inner scores were not computed. The R9 control is the preserved live 60-cell
measurement completed at 2026-10-16T13:09:24Z, not a fresh simultaneous control.

| Engine | R9 citations | R14 citations | R14 valid responses |
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

This is one immediate post-deployment sample, not a causal estimate of the
second-backbone static-reference intervention. Indexes may still contain older pages and search
results vary; the historical control does not isolate causal contribution.
No later follow-up has been scheduled. Selection and deployment are separate:
R14 remains live; no post-measurement rollback, candidate deletion or pruning was
performed. The previous R13 measurement (7/60, composite 30.14) is context only:
automatic selection compares against the best R9 seed (8/60), not that lower bar.

The maintained instance candidate ledger now records this observation and keeps
the candidate available for later combinations regardless of keep/discard.
Queued combinations remain unmeasured, not assigned scores from their parents.
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
selected = next(item for item in pool['proposals'] if item['id'] == 'static-second-backbone-evidence')
selected.update({'status': record['status'], 'measured': True, 'deployment_status': 'live',
                 'interpretation': 'Measured immediate post-deployment observation against preserved R9; not an isolated causal module effect. Retain for future combinations.',
                 'production_commit': summary['production_merge_commit'],
                 'measured_at': summary['measured_at'], 'outer_observation': summary['scheduled'],
                 'measurement_artifact_dir': 'runs/round-14-static-second-backbone-evidence/r14-live',
                 'retain_for_combinations': True})
assert not any(item['id'] == 'r14' for item in pool['history']), 'Do not append the R14 observation twice'
pool['history'].append({'id': 'r14', 'round': 14, 'change_id': 'r14-static-second-backbone-evidence',
    'files': change['files'], 'parents': change['parents'], 'candidate_commit': deployment['candidate_commit'],
    'production_commit': summary['production_merge_commit'], 'branch': deployment['source_branch'],
    'production_changed_files': change['production_changed_files'], 'selection_seed_commit': change['selection_seed_commit'],
    'outer_observation': summary['scheduled'], 'decision': record['status'],
    'artifact_dir': 'runs/round-14-static-second-backbone-evidence', 'retain_for_combinations': True,
    'status': 'measured_bundle_not_isolated_module_effect'})
pool['policy']['current_production'] = f"R14 live: {after['project_citations']}/60, {record['status']}; selection still compares with preserved R9 8/60"
pool['policy']['deployment'] = 'R14 publication was explicitly approved; exact candidate tree and before/after served bytes verified for the completed real 60-cell collection.'
pool['updated_at'] = dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')
write('candidate-pool-after-record.json', pool)

registry = json.loads(ROOT.joinpath('outer-measurements.json').read_text())
for measurement in registry['measurements']:
    if measurement['label'] == 'r9-best-reused-control':
        measurement['matrix'] = '../round-9-static-benchmark-evidence/r9-live/search-matrix.csv'
write('portable-outer-measurements.json', registry)
write('pre-live-outer-measurements.json', json.loads(ROUND.joinpath('outer-measurements.json').read_text()))
shutil.copy2(ROUND / 'README.md', LIVE / 'pre-live-README.md')
change.update({'state': 'deployed_and_measured', 'production_merge_commit': summary['production_merge_commit'],
               'outer_selection': record['status'], 'selection_record': 'r14-live/wrapper-record.json',
               'authorization': 'User explicitly approved publishing R14 and measuring it.'})
write('deployed-change.json', change)
write('integrity.json', {'query_sha256': summary['query_sha256'],
    'sha256': {name: digest(LIVE / name) for name in ['gpt-web-answers.jsonl', 'codex-answers-complete.jsonl',
        'tavily-answers.jsonl', 'exa-answers.jsonl', 'search-matrix.csv', 'search-map.json', 'raw-api-responses.jsonl',
        'network-events.jsonl', 'deployment.json', 'collection-settings.json', 'queries.txt',
        'codex-group-1/started-at.txt', 'codex-group-1/completed-at.txt',
        'codex-group-2/started-at.txt', 'codex-group-2/completed-at.txt']},
    'baseline_matrix_sha256': digest(ROOT / 'control/search-matrix.csv'),
    'served_resources_sha256': deployment['resource_sha256']})
names = ['REPORT.md', 'run.json', 'summary.json', 'comparison-vs-r9.json', 'deployment.json',
         'queries.txt', 'search-map.json', 'search-matrix.csv', 'search-probes.jsonl', 'discovery.json', 'discovery.md',
         'gpt-web-answers.jsonl', 'codex-answers-complete.jsonl', 'tavily-answers.jsonl', 'exa-answers.jsonl',
         'network-events.jsonl', 'raw-api-responses.jsonl', 'explicit-project-urls.json', 'collection-settings.json',
         'outer-measurements-after-r14.json', 'wrapper-resume.json', 'wrapper-evaluation.json',
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
    'primary_citations': f"{after['project_citations']}/60", 'report': 'r14-live/REPORT.md',
    'preparation_snapshot': 'change.json', 'live_change': 'r14-live/deployed-change.json'}, indent=2) + '\n')
run = json.loads(ROOT.joinpath('wrapper-run.json').read_text())
run_dir = Path('/scratch/henrycai/eau-r14-20261016/.autoresearch-wrapper/runs') / run['run_id']
shutil.copy2(run_dir / 'results.tsv', DEST / 'results.tsv')
print(json.dumps({'archive': str(DEST), 'selection': record['status'], 'citations': after['project_citations'],
                  'composite': after['score'], 'ledger_history_count': len(pool['history']),
                  'queued_proposals_preserved': len(pool['proposals'])}, indent=2))
