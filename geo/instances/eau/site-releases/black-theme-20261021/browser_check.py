"""Use installed Chrome on a CPU node; serve the isolated website on localhost."""
import functools
import http.server
import json
import os
import re
import subprocess
import tempfile
import threading
from html.parser import HTMLParser
from pathlib import Path

assert os.environ.get('SLURM_JOB_ID')
ROOT = Path(__file__).resolve().parent
SITE = Path('/scratch/henrycai/eau-black-theme-20261021')
CHROME = '/usr/bin/google-chrome'
harness = '''<!doctype html><html><body><pre id="results">pending</pre><iframe id="site" src="/index.html" style="width:100%;height:100vh;border:0"></iframe><script>
const frame = document.getElementById('site');
frame.onload = async () => {
  try {
    const win = frame.contentWindow, doc = win.document;
    const before = doc.getElementById('table-caption').textContent;
    const defaultButton = doc.querySelector('[data-model="qwen3"]');
    const code = [...doc.querySelectorAll('[data-code-link]')];
    const bodyBlack = win.getComputedStyle(doc.body).backgroundColor === 'rgb(0, 0, 0)';
    const visibleLinks = code.length === 2 && code.every(a => !a.hidden && a.href === 'https://github.com/StringNLPLAB/meta-agent');
    const defaultModel = defaultButton.getAttribute('aria-pressed') === 'true' && before.includes('Qwen3');
    const sprite = await (await fetch('/assets/icons.svg')).text();
    const symbols = new DOMParser().parseFromString(sprite,'image/svg+xml');
    const iconRefs = [...doc.querySelectorAll('.link-icon use')].map(u => u.getAttribute('href'));
    const iconsValid = iconRefs.length === 4 && iconRefs.every(ref => symbols.getElementById(ref.split('#')[1]));
    doc.querySelector('[data-model="qwen25"]').click();
    const secondModel = doc.getElementById('table-caption').textContent.includes('Qwen2.5') && doc.querySelector('[data-model="qwen25"]').getAttribute('aria-pressed') === 'true';
    defaultButton.click();
    const defaultRestored = doc.getElementById('table-caption').textContent === before;
    const noHorizontalOverflow = doc.documentElement.scrollWidth <= doc.documentElement.clientWidth + 1;
    const navigationFits = [...doc.querySelectorAll('nav a')].every(a => {const r = a.getBoundingClientRect(); return r.left >= 0 && r.right <= doc.documentElement.clientWidth + 1;});
    const result = {bodyBlack,visibleLinks,defaultModel,iconsValid,secondModel,defaultRestored,noHorizontalOverflow,navigationFits,iconRefs};
    result.passed = bodyBlack && visibleLinks && defaultModel && iconsValid && secondModel && defaultRestored && noHorizontalOverflow && navigationFits;
    document.getElementById('results').textContent = JSON.stringify(result);
  } catch (error) {document.getElementById('results').textContent = JSON.stringify({passed:false,error:String(error)});}
};
</script></body></html>'''

class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/__visual_check.html':
            self.send_response(200)
            self.send_header('Content-Type','text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(harness.encode())
        else:
            super().do_GET()
    def log_message(self,*args):
        pass

server = http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Handler,directory=str(SITE)))
threading.Thread(target=server.serve_forever,daemon=True).start()
url = f'http://127.0.0.1:{server.server_port}'
version = subprocess.check_output([CHROME,'--version'],text=True).strip()
base = [CHROME,'--headless=new','--no-sandbox','--disable-gpu','--disable-dev-shm-usage','--disable-background-networking',
    '--disable-sync','--no-first-run','--no-default-browser-check','--hide-scrollbars','--force-device-scale-factor=1','--virtual-time-budget=4000']

def run(name,flags,target):
    profile = tempfile.mkdtemp(prefix='eau-black-chrome-',dir=os.environ['SLURM_TMPDIR'])
    process = subprocess.run([*base,'--user-data-dir=' + profile,*flags,url + target],capture_output=True,text=True,timeout=60)
    ROOT.joinpath(name + '.stderr.txt').write_text(process.stderr)
    ROOT.joinpath(name + '.stdout.txt').write_text(process.stdout)
    process.check_returncode()
    return process.stdout

run('desktop',['--window-size=1440,1100','--screenshot=' + str(ROOT / 'desktop.png')],'/index.html')
run('mobile',['--window-size=390,1200','--screenshot=' + str(ROOT / 'mobile.png')],'/index.html')
run('results',['--window-size=1440,7600','--screenshot=' + str(ROOT / 'results.png')],'/index.html')
dom = run('interactive',['--window-size=1440,1100','--dump-dom'],'/__visual_check.html')

class Result(HTMLParser):
    active = False
    text = ''
    def handle_starttag(self,tag,attrs):
        if tag == 'pre' and dict(attrs).get('id') == 'results':
            self.active = True
    def handle_endtag(self,tag):
        if tag == 'pre':
            self.active = False
    def handle_data(self,data):
        if self.active:
            self.text += data

parser = Result()
parser.feed(dom)
checks = json.loads(parser.text)
assert checks['passed'],checks
mobile_dom = run('mobile-interactive',['--window-size=390,1200','--dump-dom'],'/__visual_check.html')
mobile_parser = Result()
mobile_parser.feed(mobile_dom)
mobile_checks = json.loads(mobile_parser.text)
assert mobile_checks['passed'],mobile_checks
result = {'passed':True,'checks':checks,'mobile_checks':mobile_checks,'chrome_version':version,'slurm_job':os.environ['SLURM_JOB_ID'],
    'screenshots':['desktop.png','mobile.png','results.png'],'site_commit':subprocess.check_output(['git','-C',str(SITE),'rev-parse','HEAD'],text=True).strip(),
    'limit':'Local HTTP browser smoke test, not a new GEO/search measurement'}
ROOT.joinpath('browser-validation.json').write_text(json.dumps(result,indent=2) + '\n')
server.shutdown()
print(json.dumps(result,indent=2))
