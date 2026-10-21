"""Complete the append-only archive after an archive-status shape assertion."""
import re
import shutil
import sys
from common import *

assert os.environ.get('SLURM_JOB_ID')
assert DEST.is_dir() and not DEST.joinpath('audit.json').exists()
change = json.loads(ROOT.joinpath('change.json').read_text())
validation = json.loads(ROOT.joinpath('validation.json').read_text())
run = json.loads(ROOT.joinpath('wrapper-run.json').read_text())
pool = json.loads(INSTANCE.joinpath('candidate-pool.json').read_text())
old = json.loads(ROOT.joinpath('candidate-pool-before.json').read_text())
worktree = Path(change['candidate']['worktree_path'])
seed_path = worktree.parent / 'seed'
assert len(validation['checks']) == 34 and all(validation['checks'].values())
assert pool['history'] == old['history'] and len(pool['history']) == 22 and pool['best_observed'] == old['best_observed']
assert len(pool['proposals']) == 16 and all(p in pool['proposals'] for p in old['proposals'])
assert git(worktree,'rev-parse','HEAD') == change['candidate_commit'] and git(worktree,'rev-parse','HEAD^{tree}') == change['candidate_tree']
assert git(PRODUCTION,'rev-parse','HEAD') == change['current_production_commit'] and not git(PRODUCTION,'status','--porcelain') and not git(worktree,'status','--porcelain')
assert git(worktree,'diff',change['selection_seed_commit'],'--name-only').splitlines() == FILES
assert git(worktree,'diff',change['current_production_commit'],'--name-only').splitlines() == DEPLOY_FILES
run_dir = SITE / '.autoresearch-wrapper/runs' / run['run_id']
for archived in sorted(DEST.rglob('*')):
    if not archived.is_file():
        continue
    relative = archived.relative_to(DEST)
    if relative.parts[0] == 'site':
        source = worktree / relative.parts[1]
    elif relative.as_posix() == 'outer-measurements.json':
        source = ROOT / 'portable-outer-measurements.json'
    elif relative.as_posix() in ['program.md','results.tsv']:
        source = run_dir / relative
    else:
        source = ROOT / relative
    assert source.is_file() and digest(source) == digest(archived),str(relative)
status = json.loads(cli('status','--json',name='wrapper-status.json'))
active = status['runs'][run['run_id']]
candidate = next(c for c in active['candidates'] if c['candidate_id'] == 'candidate-001')
assert active['status'] == 'running' and candidate['lifecycle'] == 'allocated'
assert 'latest_evaluation' not in candidate and 'result' not in candidate
assert sum('result' in c for c in active['candidates']) == 1
seed = subprocess.run([sys.executable,str(DEST / 'outer_metric.py')],cwd=seed_path,check=True,capture_output=True,text=True)
guard = subprocess.run([sys.executable,str(DEST / 'outer_metric.py')],cwd=worktree,capture_output=True,text=True)
assert seed.stdout == 'LIVE_PROJECT_CITATIONS=12/60\nMETRIC=20.0\n' and guard.returncode == 2 and 'No live measurement' in guard.stderr
manifest = json.loads(DEST.joinpath('source-evidence-manifest.json').read_text())
assert all(digest(DEST / v['path']) == v['sha256'] for v in manifest['files'].values())
assert all(DEST.joinpath('served-r21',n).read_bytes() == PRODUCTION.joinpath(n).read_bytes() for n in HTML)
for p in sorted(DEST.rglob('*')):
    if p.is_file():
        assert not re.search(r'(?i)tvly-[a-z0-9_-]{16,}|authorization:\s*bearer\s+[a-z0-9_-]{16,}|x-api-key\s*:\s*[a-z0-9_-]{16,}',p.read_text()),p.name
jobs = ['1874074','1874084','1874087','1874103']
accounting = subprocess.check_output(['sacct','--jobs',','.join(jobs),'--noheader','--parsable2','--format=JobIDRaw,JobName,State,ExitCode'],text=True)
failure = {'failed_archive_job':'1874103','stage':'Final archive status assertion, after artifact copies and metric guard checks',
    'cause':'Archive code expected status active and dict candidates; actual CLI schema is status running and list candidates',
    'effect':'No candidate edits, evaluation, score, decision, deployment or successful response affected',
    'recovery':'Append-only completion rechecks existing artifact bytes, real CLI status, historical metric and unpublished guard; preserves original failing script/provenance',
    'recovery_script':'finish_archive_r22.py','recovery_job':os.environ['SLURM_JOB_ID'],'accounting_before_recovery_completion':accounting}
DEST.joinpath('archive-recovery.json').write_text(json.dumps(failure,indent=2) + '\n')
shutil.copy2(ROOT / 'finish_archive_r22.py',DEST / 'finish_archive_r22.py')
shutil.copy2(ROOT / 'archive-1874103.out',DEST / 'archive-first-attempt.txt')
DEST.joinpath('wrapper-status.json').write_text(json.dumps(status,indent=2) + '\n')
DEST.joinpath('CURRENT.json').write_text(json.dumps({'round':22,'state':change['state'],'published':False,'measured':False,
    'candidate_commit':change['candidate_commit'],'candidate_tree':change['candidate_tree'],'best_observed_round':18,'current_production_round':21},indent=2) + '\n')
audit = {'passed':True,'local_checks':len(validation['checks']),'history_count':22,'old_proposals_preserved':15,
    'proposal_count':16,'unmeasured_proposals':2,'candidate_commit':change['candidate_commit'],'candidate_tree':change['candidate_tree'],
    'semantic_relocations':1,'text_spans':2,'new_words':False,'new_links':False,'changed_files_vs_r18':FILES,'changed_files_vs_live_r21':DEPLOY_FILES,
    'seed_metric_replay':seed.stdout.strip(),'candidate_guard_exit':guard.returncode,'archive_job':os.environ['SLURM_JOB_ID'],
    'archive_status_recovery':'archive-recovery.json; original failed script and log retained',
    'outer_status':'Unmeasured R22; explicit approval, exact deployment and complete real collection required',
    'sha256':{p.relative_to(DEST).as_posix():digest(p) for p in sorted(DEST.rglob('*')) if p.is_file()}}
DEST.joinpath('audit.json').write_text(json.dumps(audit,indent=2) + '\n')
print(json.dumps({k:v for k,v in audit.items() if k != 'sha256'},indent=2))
