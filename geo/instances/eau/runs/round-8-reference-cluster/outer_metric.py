"""Score exact deployed trees only, with the unchanged R6 site-citation definition."""
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
    print('No live measurement for this exact candidate tree. Await approved deployment, verify served bytes, then collect 60 frozen search cells.', file=sys.stderr)
    raise SystemExit(2)
measurement = matches[-1]
matrix = ROOT / measurement['matrix']
if hashlib.sha256(matrix.read_bytes()).hexdigest() != measurement['matrix_sha256']:
    raise SystemExit('Registered outer matrix changed; refusing to score.')
with matrix.open(newline='') as handle:
    rows = list(csv.DictReader(handle))
expected = {(q, engine) for q in ROOT.joinpath('queries.txt').read_text().splitlines()
            for engine in ('gpt-web', 'codex-search', 'tavily-search', 'exa-search')}
if len(rows) != 60 or {(r['query'], r['engine']) for r in rows} != expected or any(r['answer_empty'] != 'False' for r in rows):
    raise SystemExit('Incomplete or invalid four-engine response coverage; candidate remains unranked.')
citations = sum(r['site_cited'] == 'True' for r in rows)
print(f'LIVE_PROJECT_CITATIONS={citations}/60')
print(f'METRIC={100 * citations / 60}')
