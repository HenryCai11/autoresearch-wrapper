"""Record actual all-resource served verification before summarizing real probes."""
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LIVE = ROOT / 'r10-live'
SITE = Path('/project/aip-xiye17/henrycai/eau-meta-agent.github.io')
commit = subprocess.check_output(['git', '-C', str(SITE), 'rev-parse', 'HEAD'], text=True).strip()
tree = subprocess.check_output(['git', '-C', str(SITE), 'rev-parse', 'HEAD^{tree}'], text=True).strip()
assert commit == 'b70597085286d4ff4c2d3de78f25d95581835b98'
assert tree == '14fdd73cd91dc01843dbe6a57b8f172cd249ea98'
hashes = {}
for name in ['index.html', 'method.html', 'paper.html', 'research-context.html']:
    before = LIVE.joinpath('served-before', name).read_bytes()
    after = LIVE.joinpath('served-after', name).read_bytes()
    assert before == after == SITE.joinpath(name).read_bytes()
    hashes[name] = hashlib.sha256(before).hexdigest()
record = {'source_branch': 'codex/geo-live-round-10', 'candidate_commit': '04e7ea4d0b1a6be0c65301c2a297e401294a0b78',
          'production_merge_commit': commit, 'production_tree': tree, 'production_url': 'https://eau-meta-agent.github.io/',
          'resource_sha256': hashes, 'served_version_verified_at': LIVE.joinpath('verified-before.txt').read_text().strip(),
          'served_version_reverified_at': LIVE.joinpath('verified-after.txt').read_text().strip(),
          'verification': 'All four edited pages byte-match the candidate and merged production before and after search collection.',
          'authorization': 'User explicitly approved publishing and measuring R10.'}
LIVE.joinpath('deployment.json').write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(record, indent=2))
