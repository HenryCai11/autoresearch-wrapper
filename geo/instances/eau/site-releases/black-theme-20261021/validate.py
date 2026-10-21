"""Slurm-only structural/content/contrast checks for the requested visual release."""
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import xml.etree.ElementTree as ET
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse
from geo_eval.site import load_site

assert os.environ.get('SLURM_JOB_ID')
ROOT = Path(__file__).resolve().parent
WT = Path('/scratch/henrycai/eau-black-theme-20261021')
PROD = Path('/project/aip-xiye17/henrycai/eau-meta-agent.github.io')
BASE = '7eafc96a295ba8c155f7c31368b0d67d800bee20'
WRAPPER = Path('/project/aip-xiye17/henrycai/autoresearch-wrapper')
assert not ROOT.joinpath('validation.json').exists()

def git(repo,*args):
    return subprocess.check_output(['git','-C',str(repo),*args],text=True).strip()

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

class Links(HTMLParser):
    def __init__(self,text):
        super().__init__()
        self.links,self.icons,self.uses,self.ids = [],[],[],[]
        self.feed(text)
    def handle_starttag(self,tag,attrs):
        a = dict(attrs)
        if tag == 'a':
            self.links.append(a.get('href',''))
        if tag == 'svg' and a.get('class') == 'link-icon':
            self.icons.append(a)
        if tag == 'use':
            self.uses.append(a.get('href',''))
        if 'id' in a:
            self.ids.append(a['id'])

before,after = load_site(str(PROD)),load_site(str(WT))
css = WT.joinpath('styles.css').read_text()
old_html = PROD.joinpath('index.html').read_text()
new_html = WT.joinpath('index.html').read_text()
parser = Links(new_html)
old_links = Links(old_html)
icons = re.findall(r'<svg class="link-icon".*?</svg>',new_html,re.S)
root = ET.parse(WT / 'assets/icons.svg').getroot()
ns = {'svg':'http://www.w3.org/2000/svg'}
symbols = {s.attrib['id']:s for s in root.findall('svg:symbol',ns)}
official = ET.parse(ROOT / 'mark-github-16.svg').getroot().find('svg:path',ns).attrib['d']
variables = dict(re.findall(r'(--[a-z-]+):\s*(#[0-9a-fA-F]{6})',css.split('\n',2)[1]))

def luminance(color):
    parts = [int(color[i:i+2],16)/255 for i in (1,3,5)]
    values = [c/12.92 if c <= 0.04045 else ((c + 0.055)/1.055)**2.4 for c in parts]
    return sum(c*w for c,w in zip(values,[0.2126,0.7152,0.0722]))

def contrast(a,b):
    hi,lo = sorted([luminance(a),luminance(b)],reverse=True)
    return (hi + .05)/(lo + .05)

pairs = {(fg + ' on ' + bg):contrast(variables[fg],variables[bg]) for fg in ['--ink','--muted','--clay'] for bg in ['--paper','--surface','--surface-raised']}
pairs['button label on accent'] = contrast('#170c06',variables['--clay'])
checks = {
    'exact_completed_r22_parent':git(WT,'rev-parse','HEAD') == git(PROD,'rev-parse','HEAD') == BASE,
    'only_two_existing_files_changed':git(WT,'diff','--name-only').splitlines() == ['index.html','styles.css'],
    'only_icon_sprite_and_license_added':git(WT,'ls-files','--others','--exclude-standard').splitlines() == ['assets/icons.svg','assets/octicons-LICENSE.txt'],
    'black_canvas_and_native_dark_controls':variables['--paper'] == '#000000' and 'color-scheme:dark' in css,
    'dark_surfaces_used_for_sections':'.overview,.results,.resources{background:var(--surface)}' in css,
    'ten_palette_text_pairs_meet_4_5_contrast':len(pairs) == 10 and all(ratio >= 4.5 for ratio in pairs.values()),
    'css_braces_balanced':css.count('{') == css.count('}'),
    'four_icons_only_html_change':len(icons) == 4 and all(s == icons[0] or s == icons[1] for s in icons) and re.sub(r'<svg class="link-icon".*?</svg>','',new_html,flags=re.S) == old_html,
    'four_icons_decorative_with_fixed_dimensions':len(parser.icons) == 4 and all(a.get('aria-hidden') == 'true' and a.get('focusable') == 'false' and a.get('width') == a.get('height') == '18' for a in parser.icons),
    'symbol_references_valid_and_balanced':Counter(parser.uses) == Counter({'assets/icons.svg#github':2,'assets/icons.svg#paper':2}) and set(symbols) == {'github','paper'},
    'official_github_path_exactly_preserved':symbols['github'].find('svg:path',ns).attrib['d'] == official,
    'mit_license_included_unchanged':WT.joinpath('assets/octicons-LICENSE.txt').read_bytes() == ROOT.joinpath('octicons-LICENSE').read_bytes(),
    'all_visible_text_unchanged':set(before.pages) == set(after.pages) and all(after.pages[p].visible_text == page.visible_text for p,page in before.pages.items()),
    'all_hidden_text_unchanged':all(after.pages[p].hidden_text == page.hidden_text for p,page in before.pages.items()),
    'all_metadata_jsonld_unchanged':all(after.pages[p].meta == page.meta and after.pages[p].json_ld == page.json_ld for p,page in before.pages.items()),
    'all_anchor_destinations_unchanged':parser.links == old_links.links,
    'unique_ids_preserved':len(parser.ids) == len(set(parser.ids)),
    'two_code_routes_retained':parser.links.count('https://github.com/StringNLPLAB/meta-agent') == 2,
    'all_nonvisual_tracked_files_exact':all(WT.joinpath(n).read_bytes() == PROD.joinpath(n).read_bytes() for n in git(PROD,'ls-files').splitlines() if n not in ['index.html','styles.css']),
    'no_new_javascript_or_external_script':new_html.count('<script') == old_html.count('<script') and WT.joinpath('script.js').read_bytes() == PROD.joinpath('script.js').read_bytes(),
    'reduced_motion_rule_retained':'@media(prefers-reduced-motion:reduce)' in css,
    'research_figures_remain_unmodified':all(WT.joinpath(n).read_bytes() == PROD.joinpath(n).read_bytes() for n in git(PROD,'ls-files').splitlines() if n.startswith('assets/')),
}
assert all(checks.values()),[k for k,v in checks.items() if not v]
capabilities = {'playwright_python':importlib.util.find_spec('playwright') is not None,
    'chromium':next((shutil.which(n) for n in ['chromium','chromium-browser','google-chrome'] if shutil.which(n)),None)}
result = {'passed':True,'checks':checks,'contrast_ratios':pairs,'visible_home_chars':len(after.home.visible_text),
    'base_commit':BASE,'release_kind':'User-requested visual update; not a measured GEO candidate',
    'browser_test':'Not run; structural/content/contrast checks only','browser_capabilities':capabilities,'slurm_job':os.environ['SLURM_JOB_ID']}
ROOT.joinpath('validation.json').write_text(json.dumps(result,indent=2) + '\n')
subprocess.run(['git','-C',str(WT),'diff','--check'],check=True)
subprocess.run(['git','-C',str(WT),'add','--','styles.css','index.html','assets/icons.svg','assets/octicons-LICENSE.txt'],check=True)
subprocess.run(['git','-C',str(WT),'commit','-m','Use black theme and add GitHub and paper link icons'],check=True)
result.update({'candidate_commit':git(WT,'rev-parse','HEAD'),'candidate_tree':git(WT,'rev-parse','HEAD^{tree}'),'source_branch':'codex/black-theme-icons'})
ROOT.joinpath('release.json').write_text(json.dumps(result,indent=2) + '\n')
print(json.dumps({'passed':True,'checks':len(checks),'contrast_min':min(pairs.values()),'candidate_commit':result['candidate_commit'],
    'browser_capabilities':capabilities},indent=2))
