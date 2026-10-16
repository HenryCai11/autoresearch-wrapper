"""Record actual all-resource served verification before summarizing real probes."""
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LIVE = ROOT / 'r8-live'
SITE = Path('/project/aip-xiye17/henrycai/eau-meta-agent.github.io')
commit = subprocess.check_output(['git', '-C', str(SITE), 'rev-parse', 'HEAD'], text=True).strip()
tree = subprocess.check_output(['git', '-C', str(SITE), 'rev-parse', 'HEAD^{tree}'], text=True).strip()
assert commit == '4147abc262bbb69df7a170eb403bf1b6807869f4'
assert tree == 'b3d011a5256d81aac31840cc7183b8fb5fa7a405'
hashes = {}
for name in ['method.html', 'research-context.html', 'paper.html', 'llms.txt']:
    before = LIVE.joinpath('served-before', name).read_bytes()
    after = LIVE.joinpath('served-after', name).read_bytes()
    assert before == after == SITE.joinpath(name).read_bytes()
    hashes[name] = hashlib.sha256(before).hexdigest()
record = {'source_branch': 'codex/geo-live-round-8', 'candidate_commit': 'a2e3d0163fa55384c1f949b6da6c6fef1ea486fc',
          'production_merge_commit': commit, 'production_tree': tree, 'production_url': 'https://eau-meta-agent.github.io/',
          'resource_sha256': hashes, 'served_version_verified_at': LIVE.joinpath('verified-before.txt').read_text().strip(),
          'served_version_reverified_at': LIVE.joinpath('verified-after.txt').read_text().strip(),
          'verification': 'All four edited resources byte-match the candidate and merged production before and after search collection. The unchanged homepage is not used as deployment proof.',
          'authorization': 'User explicitly approved publishing and measuring R8.'}
LIVE.joinpath('deployment.json').write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(record, indent=2))
