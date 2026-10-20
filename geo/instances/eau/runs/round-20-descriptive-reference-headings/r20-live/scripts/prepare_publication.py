"""Apply the approved complete R20 candidate in an isolated deploy worktree."""
import difflib
import shutil
from common import *

assert os.environ.get('SLURM_JOB_ID')
LIVE = ROOT / 'r20-live'
DEPLOY = Path('/scratch/henrycai/eau-r20-deploy-20261019')
assert not LIVE.exists()
change = json.loads(ROOT.joinpath('change.json').read_text())
candidate = Path(change['candidate']['worktree_path'])
assert git(PRODUCTION,'rev-parse','HEAD') == change['current_production_commit']
assert git(PRODUCTION,'rev-parse','origin/main') == change['current_production_commit']
assert git(DEPLOY,'rev-parse','HEAD') == change['current_production_commit']
assert not git(PRODUCTION,'status','--porcelain') and not git(DEPLOY,'status','--porcelain')
assert git(candidate,'rev-parse','HEAD') == change['candidate_commit'] and not git(candidate,'status','--porcelain')
assert git(candidate,'rev-parse','HEAD^{tree}') == change['candidate_tree']
assert git(candidate,'diff',change['selection_seed_commit'],'HEAD','--name-only').splitlines() == FILES
assert git(candidate,'diff',change['current_production_commit'],'HEAD','--name-only').splitlines() == HTML
audit = json.loads(DEST.joinpath('audit.json').read_text())
assert audit['passed'] and audit['local_checks'] == 36
for name,sha in audit['sha256'].items():
    assert digest(DEST / name) == sha,name
assert all(json.loads(ROOT.joinpath('validation.json').read_text())['checks'].values())
expected = {name:DEPLOY.joinpath(name).read_text() for name in HTML}
for name,op in zip(HTML,json.loads(ROOT.joinpath('sources/r19-operations.json').read_text())['operations']):
    assert expected[name].count(op['after']) == 1
    expected[name] = expected[name].replace(op['after'],op['before'],1)
for name,op in zip(FILES,json.loads(ROOT.joinpath('operations.json').read_text())['operations']):
    assert expected[name].count(op['before']) == 1
    expected[name] = expected[name].replace(op['before'],op['after'],1)
assert all(expected[n] == candidate.joinpath(n).read_text() for n in HTML)
patch = ['*** Begin Patch']
for name in HTML:
    before = DEPLOY.joinpath(name).read_text().splitlines()
    after = expected[name].splitlines()
    diff = list(difflib.unified_diff(before,after,n=3,lineterm=''))[2:]
    assert diff
    patch.append('*** Update File: ' + name)
    patch.extend('@@' if line.startswith('@@') else line for line in diff)
patch.append('*** End Patch')
subprocess.run(['apply_patch','\n'.join(patch)],cwd=DEPLOY,check=True)
assert all(DEPLOY.joinpath(n).read_bytes() == candidate.joinpath(n).read_bytes() for n in HTML)
assert git(DEPLOY,'diff','--name-only').splitlines() == HTML
subprocess.run(['git','-C',str(DEPLOY),'diff','--check'],check=True)
subprocess.run(['git','-C',str(DEPLOY),'add','--',*HTML],check=True)
subprocess.run(['git','-C',str(DEPLOY),'commit','-m','Publish approved R20 reference headings on best R18 metadata'],check=True)
assert git(DEPLOY,'rev-parse','HEAD^{tree}') == change['candidate_tree']
assert not git(DEPLOY,'status','--porcelain')
subprocess.run(['git','-C',str(SITE),'merge','--ff-only',change['candidate_commit']],check=True)
LIVE.mkdir()
for name in ['served-before','served-after','gpt-web-raw','tavily-raw','exa-raw','codex-group-1','codex-group-2']:
    LIVE.joinpath(name).mkdir()
for name in ['collection-settings.json','queries.txt']:
    shutil.copy2(ROOT / name,LIVE / name)
write('publication-intent.json',{'round':20,'candidate_commit':change['candidate_commit'],'candidate_tree':change['candidate_tree'],
    'candidate_branch':'codex/geo-live-round-20','deploy_branch':'codex/geo-live-round-20-deploy',
    'deploy_commit':git(DEPLOY,'rev-parse','HEAD'),'deploy_worktree':str(DEPLOY),
    'production_parent':change['current_production_commit'],'changed_files':HTML,
    'authorization':'User explicitly requested 发布测一下 for prepared R20',
    'deployment_method':'Exact approved R18-based tree: reverse discarded R19 schema blocks in four pages plus two new H1s; apply_patch in an isolated deploy worktree; alphaXiv routes retained.'})
previous = Path('/scratch/henrycai/geo-runs/eau-r19-20261019')
for name in ['collect_api.sh','normalize_api.py','normalize_api.sh','summarize_outer_live.py','finalize_r19_measurement.py']:
    text = previous.joinpath(name).read_text().replace('r19','r20').replace('R19','R20')
    text = text.replace("'round': 19","'round': 20").replace('r20-shared-entity-combination',CHANGE_ID)
    text = text.replace("'--part', 'index.html'","'--part', 'method.html'")
    text = text.replace('R20 exact retained R10 shared-paper metadata on R18','R20 descriptive method/context H1s on best R18, without discarded R19 schema')
    target = name.replace('r19','r20')
    ROOT.joinpath(target).write_text(text)
print(json.dumps(json.loads(ROOT.joinpath('publication-intent.json').read_text()),indent=2))
