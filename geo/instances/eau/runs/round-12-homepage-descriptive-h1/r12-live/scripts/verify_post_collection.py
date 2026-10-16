"""Supplement the early after-check with a verified check after all 60 cells."""
import datetime as dt
import hashlib
import json
from pathlib import Path

LIVE = Path('/project/aip-xiye17/henrycai/autoresearch-wrapper/geo/instances/eau/runs/round-12-homepage-descriptive-h1/r12-live')
summary = json.loads(LIVE.joinpath('summary.json').read_text())
deployment = json.loads(LIVE.joinpath('deployment.json').read_text())
final_at = LIVE.joinpath('verified-final.txt').read_text().strip()
final_time = dt.datetime.fromisoformat(final_at.replace('Z', '+00:00'))
assert final_time > dt.datetime.fromisoformat(summary['measured_at'])
assert summary['scheduled']['valid_responses'] == 60
assert LIVE.joinpath('origin-main-final.txt').read_text().split()[0] == summary['production_merge_commit']
digest = hashlib.sha256(LIVE.joinpath('served-final/index.html').read_bytes()).hexdigest()
assert digest == deployment['resource_sha256']['index.html']
assert LIVE.joinpath('served-final/index.html').read_bytes() == LIVE.joinpath('served-before/index.html').read_bytes()
record = {'passed': True, 'verified_at': final_at, 'complete_summary_at': summary['measured_at'],
    'production_merge_commit': summary['production_merge_commit'], 'production_tree': summary['production_tree'],
    'resource_sha256': {'index.html': digest}, 'served_directory': 'served-final',
    'origin_ref_file': 'origin-main-final.txt',
    'note': 'The original served-after check was issued while the final Codex request was still in flight. It is retained as an intermediate check, not the authoritative end-of-collection proof. This supplemental check occurred after the completed 60-cell summary and supersedes that timing claim. No search was repeated, and no raw answers, matrix, metric or decision changed.'}
target = LIVE / 'post-collection-verification.json'
assert not target.exists()
target.write_text(json.dumps(record, indent=2) + '\n')
print(json.dumps(record, indent=2))
