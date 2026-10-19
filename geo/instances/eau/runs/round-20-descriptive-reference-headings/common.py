"""R20 helpers; Python and wrapper CLI run only inside Slurm."""
import hashlib
import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
WRAPPER = Path('/project/aip-xiye17/henrycai/autoresearch-wrapper')
INSTANCE = WRAPPER / 'geo/instances/eau'
SITE = Path('/scratch/henrycai/eau-r20-20261019')
PRODUCTION = Path('/project/aip-xiye17/henrycai/eau-meta-agent.github.io')
RUNNER = WRAPPER / 'skills/autoresearch-wrapper-run/run.sh'
DEST = INSTANCE / 'runs/round-20-descriptive-reference-headings'
SELECTED = 'descriptive-reference-headings'
CHANGE_ID = 'r20-descriptive-reference-headings'
PART = 'method.html'
FILES = ['method.html', 'research-context.html']
HTML = ['index.html', 'method.html', 'paper.html', 'research-context.html']
ALPHA = 'https://www.alphaxiv.org/abs/2610.16523'

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def write(name, value):
    ROOT.joinpath(name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')

def git(repo, *args):
    return subprocess.check_output(['git', '-C', str(repo), *args], text=True).strip()

def cli(*args, name, repo=SITE):
    env = os.environ.copy()
    env.pop('PYTHONPATH', None)
    result = subprocess.run(['bash', str(RUNNER), *args, '--repo', str(repo)], env=env, capture_output=True, text=True)
    ROOT.joinpath(name).write_text(result.stdout)
    ROOT.joinpath(name + '.stderr.txt').write_text(result.stderr)
    result.check_returncode()
    return result.stdout
