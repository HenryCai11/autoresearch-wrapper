"""Check archived measurement replay, complete cells, and retained module history."""
import csv
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
INSTANCE = Path('/project/aip-xiye17/henrycai/autoresearch-wrapper/geo/instances/eau')
ROUND = INSTANCE / 'runs/round-9-static-benchmark-evidence'
LIVE = ROUND / 'r9-live'
run_id = json.loads(ROOT.joinpath('wrapper-run.json').read_text())['run_id']
worktree_root = Path('/scratch/henrycai/eau-r9-20261016.autoresearch-worktrees') / run_id
summary = json.loads(LIVE.joinpath('summary.json').read_text())
pool = json.loads(INSTANCE.joinpath('candidate-pool.json').read_text())
assert {item['id'] for item in pool['history']} == {f'r{i}' for i in range(10)}
assert all(item['retain_for_combinations'] for item in pool['history'])
chosen = next(item for item in pool['proposals'] if item['id'] == 'static-benchmark-evidence')
assert chosen['measured'] is True and chosen['status'] == summary['decision']
assert next(item for item in pool['proposals'] if item['id'] == 'r8-reference-cluster')['measured'] is True
unmeasured = [item for item in pool['proposals'] if not item.get('measured', False)]
assert len(unmeasured) == 3
assert {item['id'] for item in pool['proposals']} == {item['id'] for item in json.loads(LIVE.joinpath('candidate-pool-before-record.json').read_text())['proposals']}
with LIVE.joinpath('search-matrix.csv').open(newline='') as handle:
    rows = list(csv.DictReader(handle))
queries = ROUND.joinpath('queries.txt').read_text().splitlines()
expected = {(q, e) for q in queries for e in ['gpt-web', 'codex-search', 'tavily-search', 'exa-search']}
assert len(rows) == 60 and {(r['query'], r['engine']) for r in rows} == expected
assert all(r['answer_empty'] == 'False' for r in rows)
citations = sum(r['site_cited'] == 'True' for r in rows)
assert citations == summary['scheduled']['project_citations']
assert summary['decision'] == ('keep' if citations > 6 else 'discard')
integrity = json.loads(LIVE.joinpath('integrity.json').read_text())
for name, value in integrity['sha256'].items():
    assert hashlib.sha256(LIVE.joinpath(name).read_bytes()).hexdigest() == value
baseline = ROUND.parent / 'round-8-reference-cluster/r8-live/search-matrix.csv'
assert hashlib.sha256(baseline.read_bytes()).hexdigest() == integrity['baseline_matrix_sha256']
for name, value in integrity['served_resources_sha256'].items():
    for phase in ['before', 'after']:
        assert hashlib.sha256(LIVE.joinpath(f'served-{phase}', name).read_bytes()).hexdigest() == value
for engine, name in [('gpt-web', 'gpt-web-answers.jsonl'), ('codex-search', 'codex-answers-complete.jsonl'),
                     ('tavily-search', 'tavily-answers.jsonl'), ('exa-search', 'exa-answers.jsonl')]:
    answers = [json.loads(line) for line in LIVE.joinpath(name).read_text().splitlines()]
    assert len(answers) == 15 and {row['query'] for row in answers} == set(queries)
    assert all(row['status'] == 'ok' and row['text'].strip() for row in answers), engine
replays = {}
for candidate in ['seed', 'candidate-001']:
    result = subprocess.run([sys.executable, str(ROUND / 'outer_metric.py')], cwd=worktree_root / candidate,
                            check=True, capture_output=True, text=True)
    expected_metric = 10.0 if candidate == 'seed' else 100 * citations / 60
    actual_metric = float(next(line.split('=', 1)[1] for line in result.stdout.splitlines() if line.startswith('METRIC=')))
    assert abs(actual_metric - expected_metric) < 1e-9
    replays[candidate] = result.stdout.strip()
script_names = ['record_deployment.py', 'summarize_outer_live.py', 'finalize_r9_measurement.py',
                'archive_r9_live.py', 'verify_served.sh', 'finish_r9.sh', 'audit_r9.py']
script_hashes = {}
for name in script_names:
    target = LIVE / 'scripts' / name
    assert not target.exists()
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / name, target)
    script_hashes[name] = hashlib.sha256(target.read_bytes()).hexdigest()
report = {'passed': True, 'cells': 60, 'project_citations': citations, 'history_count': len(pool['history']),
          'unmeasured_proposals': len(unmeasured), 'archived_metric_replays': replays, 'script_sha256': script_hashes}
LIVE.joinpath('audit.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
