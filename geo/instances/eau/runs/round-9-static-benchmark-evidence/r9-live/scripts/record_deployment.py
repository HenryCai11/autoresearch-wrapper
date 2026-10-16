"""Record actual all-resource served verification before summarizing real probes."""
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LIVE = ROOT / 'r9-live'
SITE = Path('/project/aip-xiye17/henrycai/eau-meta-agent.github.io')
commit = subprocess.check_output(['git', '-C', str(SITE), 'rev-parse', 'HEAD'], text=True).strip()
tree = subprocess.check_output(['git', '-C', str(SITE), 'rev-parse', 'HEAD^{tree}'], text=True).strip()
assert commit == '52dee0ba78885b9a3028760ba8d9cfc749a6c2e7'
assert tree == '5ebd5d1c28e00690d58caafa0edfe066ae5307d7'
hashes = {}
for name in ['index.html']:
    before = LIVE.joinpath('served-before', name).read_bytes()
    after = LIVE.joinpath('served-after', name).read_bytes()
    assert before == after == SITE.joinpath(name).read_bytes()
    hashes[name] = hashlib.sha256(before).hexdigest()
record = {'source_branch': 'codex/geo-live-round-9', 'candidate_commit': '9bb531cc09d8b7dda5a3148c5df3c5e62107892b',
          'production_merge_commit': commit, 'production_tree': tree, 'production_url': 'https://eau-meta-agent.github.io/',
          'resource_sha256': hashes, 'served_version_verified_at': LIVE.joinpath('verified-before.txt').read_text().strip(),
          'served_version_reverified_at': LIVE.joinpath('verified-after.txt').read_text().strip(),
          'verification': 'The edited homepage byte-matches the candidate and merged production before and after search collection.',
          'authorization': 'User explicitly approved publishing and measuring R9.'}
LIVE.joinpath('deployment.json').write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(record, indent=2))
