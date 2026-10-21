"""R22 publication/eval constants; Python and wrapper CLI are Slurm-only."""
import hashlib
import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
WRAPPER = Path('/project/aip-xiye17/henrycai/autoresearch-wrapper')
INSTANCE = WRAPPER / 'geo/instances/eau'
DEST = INSTANCE / 'runs/round-22-paper-project-entry'
REVISION = DEST / 'code-release'
METRIC_ROOT = Path('/scratch/henrycai/geo-runs/eau-r22-20261021')
SITE = Path('/scratch/henrycai/eau-r22-20261021')
PRODUCTION = Path('/project/aip-xiye17/henrycai/eau-meta-agent.github.io')
DEPLOY = Path('/scratch/henrycai/eau-r22-deploy-20261021')
RUNNER = WRAPPER / 'skills/autoresearch-wrapper-run/run.sh'
FILES = DEPLOY_FILES = ['README.md','index.html','llms.txt','paper.html','site-config.js']
HTML = ['index.html','method.html','paper.html','research-context.html']
SELECTED = 'paper-project-entry'
CHANGE_ID = 'r22-paper-project-entry'
PART = 'paper.html'

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def git(repo,*args):
    return subprocess.check_output(['git','-C',str(repo),*args],text=True).strip()

def write(name,value):
    ROOT.joinpath(name).write_text(json.dumps(value,ensure_ascii=False,indent=2) + '\n')

def cli(*args,name,repo=SITE):
    env = os.environ.copy()
    env.pop('PYTHONPATH',None)
    p = subprocess.run(['bash',str(RUNNER),*args,'--repo',str(repo)],env=env,capture_output=True,text=True)
    ROOT.joinpath(name).write_text(p.stdout)
    ROOT.joinpath(name + '.stderr.txt').write_text(p.stderr)
    p.check_returncode()
    return p.stdout
