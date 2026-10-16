"""Record actual all-resource served verification before summarizing real probes."""
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LIVE = ROOT / 'r11-live'
SITE = Path('/project/aip-xiye17/henrycai/eau-meta-agent.github.io')
commit = subprocess.check_output(['git', '-C', str(SITE), 'rev-parse', 'HEAD'], text=True).strip()
tree = subprocess.check_output(['git', '-C', str(SITE), 'rev-parse', 'HEAD^{tree}'], text=True).strip()
assert commit == 'c744ba125108d003ea61e8b89807e274ffaa6e4e'
assert tree == 'ccf91bf07379aae81ec4ba3c698803d0bd69368c'
hashes = {}
for name in ['index.html', 'method.html', 'paper.html', 'research-context.html']:
    before = LIVE.joinpath('served-before', name).read_bytes()
    after = LIVE.joinpath('served-after', name).read_bytes()
    assert before == after == SITE.joinpath(name).read_bytes()
    hashes[name] = hashlib.sha256(before).hexdigest()
record = {'source_branch': 'codex/geo-live-round-11-deploy', 'candidate_commit': '8e9ed309a7a60fb31cef6649f12374ad801f2a4b',
          'candidate_branch': 'codex/geo-live-round-11', 'deploy_commit': '41b1311b2d37314d5bf67419e628a6bf71782470',
          'production_merge_commit': commit, 'production_tree': tree, 'production_url': 'https://eau-meta-agent.github.io/',
          'resource_sha256': hashes, 'served_version_verified_at': LIVE.joinpath('verified-before.txt').read_text().strip(),
          'served_version_reverified_at': LIVE.joinpath('verified-after.txt').read_text().strip(),
          'verification': 'All four edited pages byte-match the candidate and merged production before and after search collection.',
          'authorization': 'User explicitly approved publishing and measuring R11, including excluding the unkept R10 metadata as documented in preparation.',
          'selection_seed': 'R9, 8/60; not the previously deployed R10 with 6/60',
          'deployment_method': 'Exact candidate files applied in an isolated branch based on R10, full tree verified before merging; a blind merge of the R9-based candidate was not used.'}
LIVE.joinpath('deployment.json').write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(record, indent=2))
