"""Check the narrow-header polish; retain both isolated visual commits."""
import json
import os
import subprocess
from pathlib import Path
from geo_eval.site import load_site

assert os.environ.get('SLURM_JOB_ID')
ROOT = Path(__file__).resolve().parent
SITE = Path('/scratch/henrycai/eau-black-theme-20261021')
BASE = Path('/project/aip-xiye17/henrycai/eau-meta-agent.github.io')
assert subprocess.check_output(['git','-C',str(SITE),'diff','--name-only'],text=True).splitlines() == ['styles.css']
before,after = load_site(str(BASE)),load_site(str(SITE))
assert all(after.pages[p].visible_text == page.visible_text and after.pages[p].json_ld == page.json_ld for p,page in before.pages.items())
subprocess.run(['git','-C',str(SITE),'diff','--check'],check=True)
subprocess.run(['git','-C',str(SITE),'add','--','styles.css'],check=True)
subprocess.run(['git','-C',str(SITE),'commit','-m','Keep all mobile navigation links inside the black theme header'],check=True)
record = json.loads(ROOT.joinpath('release.json').read_text())
record.update({'candidate_commit':subprocess.check_output(['git','-C',str(SITE),'rev-parse','HEAD'],text=True).strip(),
    'candidate_tree':subprocess.check_output(['git','-C',str(SITE),'rev-parse','HEAD^{tree}'],text=True).strip(),
    'narrow_header_polish':'Allow navigation to wrap without changing labels, destinations or text',
    'validation_job':os.environ['SLURM_JOB_ID'],'browser_test':'Final browser test follows this commit'})
ROOT.joinpath('release.json').write_text(json.dumps(record,indent=2) + '\n')
print(json.dumps({'candidate_commit':record['candidate_commit'],'candidate_tree':record['candidate_tree']},indent=2))
