"""Audit the unmeasured archive and make initial/final edit provenance explicit."""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
INSTANCE = Path('/project/aip-xiye17/henrycai/autoresearch-wrapper/geo/instances/eau')
DEST = INSTANCE / 'runs/round-10-shared-scholarly-entity'
SITE = Path('/scratch/henrycai/eau-r10-20261016')
change = json.loads(DEST.joinpath('change.json').read_text())
candidate = Path(change['candidate']['worktree_path'])
LD = re.compile(r'<script\s+type="application/ld\+json">\s*(.*?)\s*</script>', re.S)
assert not DEST.joinpath('audit.json').exists(), 'Do not replace a completed audit'


def write(name, value):
    DEST.joinpath(name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


initial = json.loads(DEST.joinpath('operations.json').read_text())
write('operations-initial-attempt.json', initial)
before = LD.search(SITE.joinpath('index.html').read_text()).group(0)
after = LD.search(candidate.joinpath('index.html').read_text()).group(0)
final_ops = {'operations': [{'op': 'replace_text', 'node': 'meta:schema', 'before': before, 'after': after}]}
write('operations.json', final_ops)
assert SITE.joinpath('index.html').read_text().replace(before, after, 1) == candidate.joinpath('index.html').read_text()
patch = ['*** Begin Patch']
for name in change['files']:
    if name == 'index.html':
        continue
    source, edited = SITE.joinpath(name).read_text(), candidate.joinpath(name).read_text()
    old_block, new_block = LD.search(source).group(0), LD.search(edited).group(0)
    assert source.replace(old_block, new_block, 1) == edited
    patch += ['*** Update File: ' + str(candidate / name), '@@']
    patch += ['-' + line for line in ('  ' + old_block).splitlines()]
    patch += ['+' + line for line in ('  ' + new_block).splitlines()]
patch.append('*** End Patch')
DEST.joinpath('support-schema-final.apply_patch').write_text('\n'.join(patch) + '\n')
mechanism = json.loads(DEST.joinpath('edit-mechanism.json').read_text())
mechanism['homepage'] = 'Initial geo-apply on meta:schema, followed by an apply_patch correction of the WebPage name to the exact head title.'
mechanism['initial_attempt_artifacts'] = ['operations-initial-attempt.json', 'preview.json', 'applied.json', 'validation-attempt-1.json', 'validate-1794060.out']
mechanism['final_artifacts'] = ['operations.json', 'support-schema-final.apply_patch', 'schema-after.json', 'candidate.patch', 'validation.json']
mechanism['corrections'] = ['Preserve two-space indentation before support-page script tags.', 'Read WebPage name from head/title, not the generic parser title that also captures SVG titles. Wrapper/scorer code remains unchanged.']
write('edit-mechanism.json', mechanism)
pool = json.loads(INSTANCE.joinpath('candidate-pool.json').read_text())
old_pool = json.loads(DEST.joinpath('candidate-pool-before.json').read_text())
assert pool['history'] == old_pool['history'] and len(pool['history']) == 10
assert {p['id'] for p in pool['proposals']} == {p['id'] for p in old_pool['proposals']}
assert all(p in pool['proposals'] for p in old_pool['proposals'] if p['id'] != 'shared-scholarly-entity')
chosen = next(p for p in pool['proposals'] if p['id'] == 'shared-scholarly-entity')
assert not chosen['measured'] and chosen['status'] == 'validated_awaiting_deployment_approval'
assert subprocess.check_output(['git', '-C', str(candidate), 'rev-parse', 'HEAD'], text=True).strip() == change['candidate_commit']
assert subprocess.check_output(['git', '-C', str(candidate), 'rev-parse', 'HEAD^{tree}'], text=True).strip() == change['candidate_tree']
assert not subprocess.check_output(['git', '-C', str(candidate), 'status', '--porcelain'], text=True).strip()
validation = json.loads(DEST.joinpath('validation.json').read_text())
assert len(validation['checks']) == 21 and all(validation['checks'].values())
seed = candidate.parent / 'seed'
replay = subprocess.run([sys.executable, str(DEST / 'outer_metric.py')], cwd=seed, capture_output=True, text=True, check=True)
assert 'LIVE_PROJECT_CITATIONS=8/60' in replay.stdout
guard = subprocess.run([sys.executable, str(DEST / 'outer_metric.py')], cwd=candidate, capture_output=True, text=True)
assert guard.returncode == 2 and 'No live measurement' in guard.stderr
environment = os.environ.copy()
environment.pop('PYTHONPATH', None)
status = subprocess.run(['bash', '/project/aip-xiye17/henrycai/autoresearch-wrapper/skills/autoresearch-wrapper-run/run.sh',
    'status', '--repo', str(SITE), '--json'], env=environment, capture_output=True, text=True, check=True)
DEST.joinpath('wrapper-status.json').write_text(status.stdout)
for name in ['audit_prepared_r10.py', 'validate-1794084.out']:
    shutil.copy2(ROOT / name, DEST / name)
shutil.copy2(ROOT / 'operations.json', DEST / 'operations-original-run-copy.json')
hashes = {path.relative_to(DEST).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(DEST.rglob('*')) if path.is_file()}
report = {'passed': True, 'local_checks': 21, 'history_count': 10, 'proposal_count': len(pool['proposals']),
    'candidate_commit': change['candidate_commit'], 'candidate_tree': change['candidate_tree'],
    'seed_metric_replay': replay.stdout.strip(), 'candidate_guard_exit': guard.returncode,
    'outer_status': 'unmeasured; approved deployment and real 60-cell collection required', 'sha256': hashes}
write('audit.json', report)
print(json.dumps({key: value for key, value in report.items() if key != 'sha256'}, indent=2))
