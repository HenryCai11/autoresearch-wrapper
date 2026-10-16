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
ROUND = INSTANCE / 'runs/round-8-reference-cluster'
LIVE = ROUND / 'r8-live'
run_id = json.loads(ROOT.joinpath('wrapper-run.json').read_text())['run_id']
worktree_root = Path('/scratch/henrycai/eau-r8-20261016.autoresearch-worktrees') / run_id
summary = json.loads(LIVE.joinpath('summary.json').read_text())
pool = json.loads(INSTANCE.joinpath('candidate-pool.json').read_text())
assert {item['id'] for item in pool['history']} == {f'r{i}' for i in range(9)}
assert all(item['retain_for_combinations'] for item in pool['history'])
chosen = next(item for item in pool['proposals'] if item['id'] == 'r8-reference-cluster')
assert chosen['measured'] is True and chosen['status'] == summary['decision'] == 'discard'
assert all(not item.get('measured', False) for item in pool['proposals'] if item['id'] != chosen['id'])
with LIVE.joinpath('search-matrix.csv').open(newline='') as handle:
    rows = list(csv.DictReader(handle))
queries = ROUND.joinpath('queries.txt').read_text().splitlines()
expected = {(q, e) for q in queries for e in ['gpt-web', 'codex-search', 'tavily-search', 'exa-search']}
assert len(rows) == 60 and {(r['query'], r['engine']) for r in rows} == expected
assert all(r['answer_empty'] == 'False' for r in rows)
assert sum(r['site_cited'] == 'True' for r in rows) == 6
replays = {}
for candidate in ['seed', 'candidate-001']:
    result = subprocess.run([sys.executable, str(ROUND / 'outer_metric.py')], cwd=worktree_root / candidate,
                            check=True, capture_output=True, text=True)
    assert 'METRIC=10.0' in result.stdout
    replays[candidate] = result.stdout.strip()
script_names = ['record_deployment.py', 'summarize_outer_live.py', 'finalize_r8_measurement.py',
                'archive_r8_live.py', 'verify_served.sh', 'finish_r8.sh', 'audit_r8.py']
script_hashes = {}
for name in script_names:
    target = LIVE / 'scripts' / name
    assert not target.exists()
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / name, target)
    script_hashes[name] = hashlib.sha256(target.read_bytes()).hexdigest()
report = {'passed': True, 'cells': 60, 'project_citations': 6, 'history_count': len(pool['history']),
          'unmeasured_proposals': 4, 'archived_metric_replays': replays, 'script_sha256': script_hashes}
LIVE.joinpath('audit.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
