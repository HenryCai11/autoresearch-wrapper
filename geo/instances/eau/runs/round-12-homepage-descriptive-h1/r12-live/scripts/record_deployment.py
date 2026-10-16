"""Record the exact R12 served homepage before judging real outer probes."""
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LIVE = ROOT / 'r12-live'
SITE = Path('/project/aip-xiye17/henrycai/eau-meta-agent.github.io')
commit = subprocess.check_output(['git', '-C', str(SITE), 'rev-parse', 'HEAD'], text=True).strip()
tree = subprocess.check_output(['git', '-C', str(SITE), 'rev-parse', 'HEAD^{tree}'], text=True).strip()
assert commit == 'bbc3b79d20323549fd29e422017ed6c457c6b707'
assert tree == 'c2e643d4d1462b72bc4914de9222cfb200be07e3'
before = LIVE.joinpath('served-before/index.html').read_bytes()
after = LIVE.joinpath('served-after/index.html').read_bytes()
assert before == after == SITE.joinpath('index.html').read_bytes()
record = {
    'source_branch': 'codex/geo-live-round-12-deploy',
    'candidate_branch': 'codex/geo-live-round-12',
    'candidate_commit': '95940d50088176ada54ea4ed829bbf4ced9c1135',
    'deploy_commit': '370c111915310be9ce80fe4202d9ae7bd1a4e7ec',
    'production_merge_commit': commit, 'production_tree': tree,
    'production_url': 'https://eau-meta-agent.github.io/',
    'resource_sha256': {'index.html': hashlib.sha256(before).hexdigest()},
    'served_version_verified_at': LIVE.joinpath('verified-before.txt').read_text().strip(),
    'served_version_reverified_at': LIVE.joinpath('verified-after.txt').read_text().strip(),
    'verification': 'The only changed resource, index.html, byte-matches the candidate and production before and after all searches; full production tree equals candidate.',
    'authorization': 'User explicitly confirmed publishing and testing R12, then preparing the next round.',
    'selection_seed': 'R9, 8/60; not previous R11 production with 7/60',
    'deployment_method': 'Isolated deploy branch based on R11; exact candidate index.html and complete candidate tree verified before merge. Relative to R11, the homepage restores the R9 overview as well as testing its H1.'
}
LIVE.joinpath('deployment.json').write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(record, indent=2))
