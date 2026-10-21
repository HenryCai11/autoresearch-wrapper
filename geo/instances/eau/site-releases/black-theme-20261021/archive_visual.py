"""Track the requested published visual release without inheriting GEO scores."""
import copy
import datetime as dt
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

assert os.environ.get('SLURM_JOB_ID')
ROOT = Path(__file__).resolve().parent
WRAPPER = Path('/project/aip-xiye17/henrycai/autoresearch-wrapper')
INSTANCE = WRAPPER / 'geo/instances/eau'
ROUND = INSTANCE / 'runs/round-22-paper-project-entry'
DEST = INSTANCE / 'site-releases/black-theme-20261021'
SITE = Path('/project/aip-xiye17/henrycai/eau-meta-agent.github.io')
WT = Path('/scratch/henrycai/eau-black-theme-20261021')
assert not DEST.exists() and ROOT.joinpath('served-verified-at.txt').is_file()

def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def git(repo,*args):
    return subprocess.check_output(['git','-C',str(repo),*args],text=True).strip()

published = json.loads(ROOT.joinpath('published.json').read_text())
release = json.loads(ROOT.joinpath('release.json').read_text())
browser = json.loads(ROOT.joinpath('browser-validation.json').read_text())
assert browser['passed'] and browser['checks']['passed'] and browser['mobile_checks']['passed']
assert browser['site_commit'] == release['candidate_commit'] == git(WT,'rev-parse','HEAD')
assert git(SITE,'rev-parse','HEAD') == published['production_commit'] and git(SITE,'rev-parse','HEAD^{tree}') == published['tree'] == release['candidate_tree']
assert not git(SITE,'status','--porcelain') and not git(WT,'status','--porcelain')
assert git(SITE,'diff',published['measured_r22_commit'],'HEAD','--name-only').splitlines() == ['assets/icons.svg','assets/octicons-LICENSE.txt','index.html','styles.css']
attempts = [json.loads(l) for l in ROOT.joinpath('served-attempts.jsonl').read_text().splitlines()]
assert attempts[-1]['matched'] is True
served = Path(attempts[-1]['served_dir'])
files = ['index.html','styles.css','assets/icons.svg','assets/octicons-LICENSE.txt']
assert all(served.joinpath(n).read_bytes() == SITE.joinpath(n).read_bytes() == WT.joinpath(n).read_bytes() for n in files)
live_audit = json.loads(ROUND.joinpath('r22-live/audit.json').read_text())
assert live_audit['passed'] and all(digest(ROUND / 'r22-live' / n) == sha for n,sha in live_audit['sha256'].items())
assert published['tree'] != live_audit['measured_tree'] and published['production_commit'] != live_audit['production_commit']
guard = subprocess.run([sys.executable,str(ROUND / 'outer_metric.py')],cwd=SITE,capture_output=True,text=True)
assert guard.returncode == 2 and 'No live measurement' in guard.stderr
pool_path = INSTANCE / 'candidate-pool.json'
pool = json.loads(pool_path.read_text())
old_pool = copy.deepcopy(pool)
assert len(pool['history']) == 23 and len(pool['proposals']) == 16 and pool['best_observed']['round'] == 18
latest = {**published,'source_branch':release['source_branch'],'source_commit':release['candidate_commit'],
    'artifact_dir':'site-releases/black-theme-20261021','served_verified_at':ROOT.joinpath('served-verified-at.txt').read_text().strip(),
    'browser_validation':'browser-validation.json','geo_status':'Not measured; R22 score belongs only to its earlier exact tree',
    'resource_sha256':{n:digest(served / n) for n in files}}
pool['latest_site_release'] = latest
pool['policy']['current_production'] = 'Black theme/icons user visual release ' + published['production_commit'] + '; unmeasured GEO tree. Earlier R22 12/60 is historical and not inherited.'
pool['policy']['user_presentation_constraint'] = 'Preserve the user-requested black background and GitHub/paper icons in future website candidates unless the user asks to change them; do not silently reset presentation to an old GEO seed.'
chosen = next(p for p in pool['proposals'] if p['id'] == 'paper-project-entry')
chosen['deployment_status'] = 'superseded_by_user_visual_release'
chosen['superseding_release'] = 'site-releases/black-theme-20261021'
assert pool['history'] == old_pool['history'] and pool['best_observed'] == old_pool['best_observed']
assert [p for p in pool['proposals'] if p['id'] != chosen['id']] == [p for p in old_pool['proposals'] if p['id'] != chosen['id']]
pool['updated_at'] = dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')
DEST.mkdir(parents=True)
for name in ['release.json','validation.json','browser-validation.json','published.json','served-attempts.jsonl','served-verified-at.txt','origin-main.txt',
    'desktop.png','mobile.png','results.png','validate.py','validate.sh','browser_check.py','browser_check.sh','finalize_visual.py','final_check.sh','verify_live.sh','archive_visual.py','archive_visual.sh']:
    shutil.copy2(ROOT / name,DEST / name)
for name in files:
    target = DEST / 'served' / name
    target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(served / name,target)
DEST.joinpath('sources').mkdir()
for name in ['mark-github-16.svg','octicons-LICENSE']:
    shutil.copy2(ROOT / name,DEST / 'sources' / name)
DEST.joinpath('unmeasured-metric-guard.txt').write_text(guard.stderr)
DEST.joinpath('deployment.json').write_text(json.dumps(latest,indent=2) + '\n')
DEST.joinpath('candidate-pool-before.json').write_text(json.dumps(old_pool,ensure_ascii=False,indent=2) + '\n')
DEST.joinpath('candidate-pool-after.json').write_text(json.dumps(pool,ensure_ascii=False,indent=2) + '\n')
DEST.joinpath('README.md').write_text(f'''# Black theme and link icons — user-requested visual release

Published production `{published['production_commit']}`, tree `{published['tree']}`,
source branch `{release['source_branch']}`, source commit `{release['candidate_commit']}`.
Explicit authorization: black background, icons such as GitHub, then direct push.
All four changed served resources match the exact production/worktree bytes at
{latest['served_verified_at']}. Initial stale CDN checks are retained.

Black page canvas, dark panels, light text and existing warm/sage accents cover
the shared stylesheet. Adapted charts/diagram/citation panels retain all data.
Two Code links use GitHub marks and two alphaXiv buttons use document icons;
text labels, destinations, accessibility and external-link behavior remain.
Icons are local SVG symbols with the official primer/octicons GitHub path and
included MIT license; the document symbol is a simple original outline.
Narrow-screen navigation wraps to keep every link inside the viewport.

22 structural/content/contrast checks passed before narrow-screen polish;
ten palette text contrasts are at least 7.9:1. Final real Chrome desktop and
narrow-screen checks confirm black body, visible code links, valid icon symbols,
default and second-model switching/restoration, no horizontal overflow and
navigation within the viewport. Screenshots are desktop.png, mobile.png and
results.png (full page, including the result area). Initial anchor-scrolled
capture was empty, so final capture uses a full-height viewport; no website
content was changed for screenshotting. Browser jobs run on Slurm CPU nodes,
with ephemeral profiles in SLURM_TMPDIR, durable outputs in scratch. No package
installation, login-node browser/Python/Node or local model inference.

Only index.html, styles.css and the two icon/license assets differ from the
previous measured R22 production. Visible text, link destinations, research
figures, numerical results, metadata/JSON-LD, code URL and all alphaXiv routing
remain unchanged. The six source-code/reading entry labels remain accessible.

This release is **not a GEO measurement**. R22's 12/60 primary and 30.47 composite
belong to the earlier exact tree `{live_audit['measured_tree']}` at production
`{live_audit['production_commit']}`. The archived metric correctly rejects this
new tree with exit 2. No extra paid search, inner score, new optimization round,
candidate promotion, rollback, pruning or deletion was performed. All 23
historical observations, sixteen proposals and best R18 remain unchanged;
only current deployment pointers and user presentation constraints are updated.
''')
shutil.copy2(ROUND / 'CURRENT.json',DEST / 'pre-visual-CURRENT.json')
shutil.copy2(ROUND / 'README.md',DEST / 'pre-visual-README.md')
current = {'round':22,'state':'measured_r22_superseded_by_user_visual_release',
    'measured_r22_candidate':live_audit['candidate_commit'],'measured_r22_production':live_audit['production_commit'],
    'measured_r22_tree':live_audit['measured_tree'],'report':'r22-live/REPORT.md','primary_citations':'12/60','decision':'discard',
    'latest_site_release':'../../site-releases/black-theme-20261021','latest_site_commit':published['production_commit'],
    'latest_site_tree':published['tree'],'latest_site_geo_measured':False,'best_observed_round':18}
ROUND.joinpath('CURRENT.json').write_text(json.dumps(current,indent=2) + '\n')
ROUND.joinpath('README.md').write_text('Current website: user-requested black theme/icon release, separately published and not GEO-measured; see [release](../../site-releases/black-theme-20261021/README.md) and CURRENT.json. The R22 score below belongs only to the earlier exact tested tree.\n\n' + DEST.joinpath('pre-visual-README.md').read_text())
pool_path.write_text(json.dumps(pool,ensure_ascii=False,indent=2) + '\n')
accounting = subprocess.check_output(['sacct','--jobs','1875757,1875777,1875792,1875799','--noheader','--parsable2','--format=JobIDRaw,JobName,State,ExitCode'],text=True)
DEST.joinpath('slurm-provenance.json').write_text(json.dumps({'validation_and_browser_jobs':accounting,'archive_job':os.environ['SLURM_JOB_ID']},indent=2) + '\n')
audit = {'passed':True,'production_commit':published['production_commit'],'tree':published['tree'],'served_resources':4,'real_browser_checks':True,
    'history_count':23,'proposal_count':16,'best_observed_round':18,'new_geo_measurement':False,'new_tree_metric_guard_exit':2,
    'r22_audit_sha256':digest(ROUND / 'r22-live/audit.json'),'sha256':{p.relative_to(DEST).as_posix():digest(p) for p in sorted(DEST.rglob('*')) if p.is_file()}}
DEST.joinpath('audit.json').write_text(json.dumps(audit,indent=2) + '\n')
print(json.dumps({k:v for k,v in audit.items() if k != 'sha256'},indent=2))
