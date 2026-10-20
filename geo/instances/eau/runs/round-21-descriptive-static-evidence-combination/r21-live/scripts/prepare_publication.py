"""Replay the approved R18/R14 candidate on verified current R20 production."""
import difflib
import shutil
from common import *

assert os.environ.get('SLURM_JOB_ID')
LIVE = ROOT / 'r21-live'
DEPLOY = Path('/scratch/henrycai/eau-r21-deploy-20261020')
assert not LIVE.exists()
change = json.loads(ROOT.joinpath('change.json').read_text())
run = json.loads(ROOT.joinpath('wrapper-run.json').read_text())
candidate = Path(change['candidate']['worktree_path'])
assert git(PRODUCTION,'rev-parse','HEAD') == git(PRODUCTION,'rev-parse','origin/main') == change['current_production_commit']
assert git(DEPLOY,'rev-parse','HEAD') == change['current_production_commit']
assert not git(PRODUCTION,'status','--porcelain') and not git(DEPLOY,'status','--porcelain')
assert git(candidate,'rev-parse','HEAD') == change['candidate_commit'] and not git(candidate,'status','--porcelain')
assert git(candidate,'rev-parse','HEAD^{tree}') == change['candidate_tree']
assert git(candidate,'diff',change['selection_seed_commit'],'HEAD','--name-only').splitlines() == FILES
assert git(candidate,'diff',change['current_production_commit'],'HEAD','--name-only').splitlines() == DEPLOY_FILES
audit = json.loads(DEST.joinpath('audit.json').read_text())
assert audit['passed'] and audit['local_checks'] == 39
for name,sha in audit['sha256'].items():
    assert digest(DEST / name) == sha,name
assert all(json.loads(ROOT.joinpath('validation.json').read_text())['checks'].values())
status = json.loads(cli('status','--json',name='wrapper-before-publication.json'))
active = status['runs'][run['run_id']]
assert active['status'] == 'running' and active['rounds_completed'] == 0 and active['best_metric'] == 20.0
expected = {n:DEPLOY.joinpath(n).read_text() for n in HTML}
for op in json.loads(ROOT.joinpath('parents/r20-operations.json').read_text())['operations']:
    name = op['node'][5:]
    assert expected[name].count(op['after']) == 1
    expected[name] = expected[name].replace(op['after'],op['before'],1)
op = json.loads(ROOT.joinpath('operations.json').read_text())['operations'][0]
assert expected['index.html'].count(op['before']) == 1
expected['index.html'] = expected['index.html'].replace(op['before'],op['after'],1)
assert all(expected[n] == candidate.joinpath(n).read_text() for n in HTML)
patch = ['*** Begin Patch']
for name in DEPLOY_FILES:
    before = DEPLOY.joinpath(name).read_text().splitlines()
    after = expected[name].splitlines()
    diff = list(difflib.unified_diff(before,after,n=3,lineterm=''))[2:]
    assert diff
    patch += ['*** Update File: ' + name]
    patch += ['@@' if line.startswith('@@') else line for line in diff]
patch += ['*** End Patch']
subprocess.run(['apply_patch','\n'.join(patch)],cwd=DEPLOY,check=True)
assert all(DEPLOY.joinpath(n).read_bytes() == candidate.joinpath(n).read_bytes() for n in HTML)
assert git(DEPLOY,'diff','--name-only').splitlines() == DEPLOY_FILES
subprocess.run(['git','-C',str(DEPLOY),'diff','--check'],check=True)
subprocess.run(['git','-C',str(DEPLOY),'add','--',*DEPLOY_FILES],check=True)
subprocess.run(['git','-C',str(DEPLOY),'commit','-m','Publish approved R21 retained second-backbone evidence on best R18'],check=True)
assert git(DEPLOY,'rev-parse','HEAD^{tree}') == change['candidate_tree'] and not git(DEPLOY,'status','--porcelain')
subprocess.run(['git','-C',str(SITE),'merge','--ff-only',change['candidate_commit']],check=True)
LIVE.mkdir()
for name in ['served-before','served-after','gpt-web-raw','tavily-raw','exa-raw','codex-group-1','codex-group-2']:
    LIVE.joinpath(name).mkdir()
for name in ['collection-settings.json','queries.txt']:
    shutil.copy2(ROOT / name,LIVE / name)
write('publication-intent.json',{'round':21,'candidate_commit':change['candidate_commit'],'candidate_tree':change['candidate_tree'],
    'candidate_branch':'codex/geo-live-round-21','deploy_branch':'codex/geo-live-round-21-deploy',
    'deploy_commit':git(DEPLOY,'rev-parse','HEAD'),'deploy_worktree':str(DEPLOY),'production_parent':change['current_production_commit'],
    'changed_files':DEPLOY_FILES,'authorization':'User explicitly requested publishing and testing prepared R21',
    'deployment_method':'Exact approved R18-based tree: replay final retained R14 table in index.html and restore R18 method/context H1s instead of inheriting discarded R20 headings; apply_patch in isolated deploy worktree. Full tree and alphaXiv routes verified.'})
previous = Path('/scratch/henrycai/geo-runs/eau-r20-20261019')
names = ['collect_api.sh','normalize_api.py','normalize_api.sh','summarize_outer_live.py','finalize_r20_measurement.py',
    'record_deployment.py','collect_codex_network.sh','probe_codex_native.sh']
for name in names:
    text = previous.joinpath(name).read_text().replace(str(previous),str(ROOT)).replace('r20','r21').replace('R20','R21')
    text = text.replace("'round': 20","'round': 21").replace('r21-descriptive-reference-headings',CHANGE_ID)
    text = text.replace("'--part', 'method.html'","'--part', 'index.html'")
    text = text.replace('R21 descriptive method/context H1s on best R18, without discarded R19 schema','R21 exact retained R14 static table on R18; discarded R20 H1s not inherited')
    text = text.replace('four served pages','three changed served pages').replace('four changed resources','three changed resources')
    text = text.replace('all four changed served resources','all three changed served resources').replace('four-page served checks','three-page served checks')
    if name == 'record_deployment.py':
        text = text.replace('for name in HTML:','for name in DEPLOY_FILES:')
        text = text.replace("'changed_files_vs_live_r19':HTML","'changed_files_vs_live_r20':DEPLOY_FILES")
        text = text.replace('not tied R19 matrix','not tied R20 matrix')
    ROOT.joinpath(name.replace('r20','r21')).write_text(text)
print(json.dumps(json.loads(ROOT.joinpath('publication-intent.json').read_text()),indent=2))
