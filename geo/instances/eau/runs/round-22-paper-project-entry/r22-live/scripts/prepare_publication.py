"""Deploy only the explicitly approved latest R22 code-release tree."""
import difflib
import shutil
from common import *

assert os.environ.get('SLURM_JOB_ID')
LIVE = ROOT / 'r22-live'
assert not LIVE.exists()
change = json.loads(ROOT.joinpath('change.json').read_text())
candidate = Path(change['candidate']['worktree_path'])
assert change['candidate_commit'] == 'fae44609023fddc240a13502f77abcfcd925c95d'
assert change['candidate_tree'] == '1ac57c63402d39d6f7738414ff00bf9837305759'
assert git(PRODUCTION,'rev-parse','HEAD') == git(PRODUCTION,'rev-parse','origin/main') == git(DEPLOY,'rev-parse','HEAD') == change['current_production_commit']
assert all(not git(p,'status','--porcelain') for p in [PRODUCTION,DEPLOY,candidate,SITE])
assert git(candidate,'rev-parse','HEAD') == change['candidate_commit'] and git(candidate,'rev-parse','HEAD^{tree}') == change['candidate_tree']
assert all(git(candidate,'diff',change[key],'HEAD','--name-only').splitlines() == FILES for key in ['selection_seed_commit','current_production_commit'])
old_audit = json.loads(DEST.joinpath('audit.json').read_text())
for name,sha in old_audit['sha256'].items():
    p = REVISION / 'preimages' / name if name in ['README.md','CURRENT.json'] else DEST / name
    assert digest(p) == sha,name
audit = json.loads(REVISION.joinpath('audit.json').read_text())
assert audit['passed'] and audit['checks'] == 28 and all(digest(REVISION / n) == sha for n,sha in audit['sha256'].items())
assert json.loads(DEST.joinpath('CURRENT.json').read_text())['candidate_commit'] == change['candidate_commit']
assert all(json.loads(REVISION.joinpath('validation.json').read_text())['checks'].values())
active = json.loads(cli('status','--json',name='wrapper-before-publication.json'))['runs'][change['wrapper_run_id']]
assert active['status'] == 'running' and active['rounds_completed'] == 0 and active['best_metric'] == 20.0
assert next(c for c in active['candidates'] if c['candidate_id'] == 'candidate-001')['lifecycle'] == 'allocated'
patch = ['*** Begin Patch']
for name in FILES:
    before,after = [p.joinpath(name).read_text().splitlines() for p in [DEPLOY,candidate]]
    diff = list(difflib.unified_diff(before,after,n=3,lineterm=''))[2:]
    assert diff
    patch += ['*** Update File: ' + name] + ['@@' if line.startswith('@@') else line for line in diff]
patch += ['*** End Patch']
subprocess.run(['apply_patch','\n'.join(patch)],cwd=DEPLOY,check=True)
assert git(DEPLOY,'diff','--name-only').splitlines() == FILES
subprocess.run(['git','-C',str(DEPLOY),'diff','--check'],check=True)
subprocess.run(['git','-C',str(DEPLOY),'add','--',*FILES],check=True)
subprocess.run(['git','-C',str(DEPLOY),'commit','-m','Publish approved R22 paper entry and released meta-agent code links'],check=True)
assert git(DEPLOY,'rev-parse','HEAD^{tree}') == change['candidate_tree']
assert all(DEPLOY.joinpath(n).read_bytes() == candidate.joinpath(n).read_bytes() for n in git(candidate,'ls-files').splitlines())
subprocess.run(['git','-C',str(SITE),'merge','--ff-only',change['candidate_commit']],check=True)
LIVE.mkdir()
for n in ['served-before','served-after','gpt-web-raw','tavily-raw','exa-raw','codex-group-1','codex-group-2']:
    LIVE.joinpath(n).mkdir()
for n in ['queries.txt','collection-settings.json']:
    shutil.copy2(ROOT / n,LIVE / n)
queries = ROOT.joinpath('queries.txt').read_text().splitlines()
for g,items in [(1,queries[:8]),(2,queries[8:])]:
    LIVE.joinpath(f'codex-group-{g}/queries.txt').write_text('\n'.join(items) + '\n')
write('publication-intent.json',{'round':22,'revision':'code-release','candidate_commit':change['candidate_commit'],'candidate_tree':change['candidate_tree'],
    'candidate_branch':'codex/geo-live-round-22','deploy_branch':'codex/geo-live-round-22-deploy','deploy_commit':git(DEPLOY,'rev-parse','HEAD'),
    'deploy_worktree':str(DEPLOY),'production_parent':change['current_production_commit'],'changed_files':FILES,
    'authorization':'User explicitly requested publishing and testing the latest R22 after the code-link update',
    'deployment_method':'Exact latest R18-based R22 tree: original paper-paragraph relocation plus four-file user-requested code release; remove unkept R21 table. apply_patch in isolated deploy worktree; full tree and all alphaXiv routes verified.'})
print(ROOT.joinpath('publication-intent.json').read_text())
