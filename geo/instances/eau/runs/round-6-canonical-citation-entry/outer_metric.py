"""Only return a metric for this exact site's tree when a live search measurement exists."""
import csv
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
query_hash = hashlib.sha256(ROOT.joinpath('queries.txt').read_bytes()).hexdigest()
tree = subprocess.check_output(['git', 'rev-parse', 'HEAD^{tree}'], text=True).strip()
registry = json.loads(ROOT.joinpath('outer-measurements.json').read_text())
matches = [r for r in registry['measurements'] if r['deployed_tree'] == tree and r['query_sha256'] == query_hash]
if not matches:
    print('No live measurement exists for this candidate tree. Deploy and verify the exact tree, then collect the frozen four-engine probes before evaluate.', file=sys.stderr)
    raise SystemExit(2)
measurement = matches[-1]
matrix_path = Path(measurement['matrix'])
if not matrix_path.is_absolute():
    matrix_path = ROOT / matrix_path
rows = list(csv.DictReader(matrix_path.open()))
expected = {(query, engine) for query in ROOT.joinpath('queries.txt').read_text().splitlines()
            for engine in ('gpt-web', 'codex-search', 'tavily-search', 'exa-search')}
assert {(r['query'], r['engine']) for r in rows} == expected
if len(rows) != 60 or any(r['answer_empty'] != 'False' for r in rows):
    print('Incomplete four-engine response coverage; do not rank a candidate from failed-tool cells.', file=sys.stderr)
    raise SystemExit(2)
cited = sum(r['site_cited'] == 'True' for r in rows)
print(f'LIVE_PROJECT_CITATIONS={cited}/60')
print('METRIC=' + str(100 * cited / len(rows)))
