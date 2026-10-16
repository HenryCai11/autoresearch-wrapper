"""Append measured R8 evidence and update the maintained module candidate ledger."""
import datetime as dt
import hashlib
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LIVE = ROOT / 'r8-live'
INSTANCE = Path('/project/aip-xiye17/henrycai/autoresearch-wrapper/geo/instances/eau')
ROUND = INSTANCE / 'runs/round-8-reference-cluster'
DEST = ROUND / 'r8-live'
summary = json.loads(LIVE.joinpath('summary.json').read_text())
record = json.loads(LIVE.joinpath('wrapper-record.json').read_text())
deployment = json.loads(LIVE.joinpath('deployment.json').read_text())
change = json.loads(ROOT.joinpath('change.json').read_text())
control = json.loads(ROOT.joinpath('r7-control/summary.json').read_text())
before = summary['matched_valid_comparison']['baseline']
after = summary['matched_valid_comparison']['r8']
assert summary['scheduled']['valid_responses'] == before['n'] == 60
assert record['status'] == summary['decision']


def write(name, value):
    LIVE.joinpath(name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


body = f'''# EAU R8 — cross-module reference cluster, live outer measurement

R8 was approved, merged and published as `{summary['production_merge_commit']}`.
All four changed resources (`method.html`, `research-context.html`, `paper.html`,
`llms.txt`) byte-matched the candidate before and after collection. The unchanged
homepage was not used as proof of deployment. Verification began at
{deployment['served_version_verified_at']}.

This candidate connects the existing R2/R3/R4 reference modules using the R6
explicit-canonical-entry idea on the deployed R7 base. It adds nine distinct local
reference edges, not nine measured search gains. Main content, facts, homepage,
metadata, styles, scripts and scorer are unchanged.

The decision metric remains the frozen four-engine project-domain citation rate.
Inner scores were not computed. The R7 control is the preserved live 60-cell
measurement completed at 2026-10-16T12:00:17Z, not a fresh simultaneous control.

| Engine | R7 citations | R8 citations | R8 valid responses |
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
reference bundle. Indexes may still contain older pages, search results vary,
and this bundled test does not isolate an individual module's contribution.
No later follow-up has been scheduled. Selection and deployment are separate:
R8 remains live; no rollback, candidate deletion or branch pruning was performed.

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
selected = next(item for item in pool['proposals'] if item['id'] == 'r8-reference-cluster')
selected.update({'status': record['status'], 'measured': True, 'deployment_status': 'live',
                 'production_commit': summary['production_merge_commit'],
                 'measured_at': summary['measured_at'], 'outer_observation': summary['scheduled'],
                 'measurement_artifact_dir': 'runs/round-8-reference-cluster/r8-live',
                 'retain_for_combinations': True})
assert not any(item['id'] == 'r8' for item in pool['history']), 'Do not append the R8 observation twice'
pool['history'].append({'id': 'r8', 'round': 8, 'change_id': 'r8-reference-cluster',
    'files': change['files'], 'parents': change['parents'], 'candidate_commit': deployment['candidate_commit'],
    'production_commit': summary['production_merge_commit'], 'branch': deployment['source_branch'],
    'outer_observation': summary['scheduled'], 'decision': record['status'],
    'artifact_dir': 'runs/round-8-reference-cluster', 'retain_for_combinations': True,
    'status': 'measured_bundle_not_isolated_module_effect'})
pool['updated_at'] = dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')
write('candidate-pool-after-record.json', pool)

registry = json.loads(ROOT.joinpath('outer-measurements.json').read_text())
for measurement in registry['measurements']:
    if measurement['label'] == 'r7-live-reused-control':
        measurement['matrix'] = '../round-7-static-mechanism-overview/r7-live/search-matrix.csv'
write('portable-outer-measurements.json', registry)
write('pre-live-outer-measurements.json', json.loads(ROUND.joinpath('outer-measurements.json').read_text()))
change.update({'state': 'deployed_and_measured', 'production_merge_commit': summary['production_merge_commit'],
               'outer_selection': record['status'], 'selection_record': 'r8-live/wrapper-record.json',
               'authorization': 'User explicitly approved publishing R8 and measuring it.'})
write('deployed-change.json', change)
write('integrity.json', {'query_sha256': summary['query_sha256'],
    'sha256': {name: digest(LIVE / name) for name in ['gpt-web-answers.jsonl', 'codex-answers-complete.jsonl',
        'tavily-answers.jsonl', 'exa-answers.jsonl', 'search-matrix.csv', 'search-map.json', 'raw-api-responses.jsonl']},
    'baseline_matrix_sha256': digest(ROOT / 'r7-control/search-matrix.csv'),
    'served_resources_sha256': deployment['resource_sha256']})
names = ['REPORT.md', 'run.json', 'summary.json', 'comparison-vs-r7.json', 'deployment.json',
         'queries.txt', 'search-map.json', 'search-matrix.csv', 'search-probes.jsonl', 'discovery.json', 'discovery.md',
         'gpt-web-answers.jsonl', 'codex-answers-complete.jsonl', 'tavily-answers.jsonl', 'exa-answers.jsonl',
         'network-events.jsonl', 'raw-api-responses.jsonl', 'explicit-project-urls.json',
         'outer-measurements-after-r8.json', 'wrapper-resume.json', 'wrapper-evaluation.json',
         'wrapper-record.json', 'wrapper-status.json', 'origin-main-before.txt', 'origin-main-after.txt',
         'verified-before.txt', 'verified-after.txt', 'candidate-pool-before-record.json', 'candidate-pool-after-record.json',
         'portable-outer-measurements.json', 'pre-live-outer-measurements.json', 'deployed-change.json', 'integrity.json']
for phase in ['before', 'after']:
    names += [f'served-{phase}/{name}' for name in change['files']]
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
    'primary_citations': f"{after['project_citations']}/60", 'report': 'r8-live/REPORT.md',
    'preparation_snapshot': 'change.json', 'live_change': 'r8-live/deployed-change.json'}, indent=2) + '\n')
run = json.loads(ROOT.joinpath('wrapper-run.json').read_text())
run_dir = Path('/scratch/henrycai/eau-r8-20261016/.autoresearch-wrapper/runs') / run['run_id']
shutil.copy2(run_dir / 'results.tsv', DEST / 'results.tsv')
print(json.dumps({'archive': str(DEST), 'selection': record['status'], 'citations': after['project_citations'],
                  'composite': after['score'], 'ledger_history_count': len(pool['history']),
                  'queued_proposals_preserved': len(pool['proposals'])}, indent=2))
