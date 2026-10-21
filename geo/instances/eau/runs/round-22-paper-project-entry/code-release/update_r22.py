"""Validate and retain a user-requested code-link revision of unpublished R22."""
import copy
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote,urlparse
from geo_eval.site import load_site

assert os.environ.get('SLURM_JOB_ID')
ROOT = Path(__file__).resolve().parent
WRAPPER = Path('/project/aip-xiye17/henrycai/autoresearch-wrapper')
INSTANCE = WRAPPER / 'geo/instances/eau'
ROUND = INSTANCE / 'runs/round-22-paper-project-entry'
DEST = ROUND / 'code-release'
SITE = Path('/scratch/henrycai/eau-r22-20261021')
WT = Path('/scratch/henrycai/eau-r22-20261021.autoresearch-worktrees/20261021T090905Z-paper-html/candidate-001')
PRODUCTION = Path('/project/aip-xiye17/henrycai/eau-meta-agent.github.io')
RUNNER = WRAPPER / 'skills/autoresearch-wrapper-run/run.sh'
METRIC = Path('/scratch/henrycai/geo-runs/eau-r22-20261021/outer_metric.py')
CODE = 'https://github.com/StringNLPLAB/meta-agent'
OLD = 'aa3c0ea81c62f6a3cc263432ea625f69030d9edd'
RUN = '20261021T090905Z-paper-html'
FILES = ['README.md','index.html','llms.txt','site-config.js']
ALL_FILES = ['README.md','index.html','llms.txt','paper.html','site-config.js']
HTML = ['index.html','method.html','paper.html','research-context.html']
assert not DEST.exists() and not ROOT.joinpath('validation.json').exists()

def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def write(name,value):
    ROOT.joinpath(name).write_text(json.dumps(value,ensure_ascii=False,indent=2) + '\n')

def git(repo,*args):
    return subprocess.check_output(['git','-C',str(repo),*args],text=True).strip()

def cli(*args,name,repo=SITE):
    env = os.environ.copy()
    env.pop('PYTHONPATH',None)
    p = subprocess.run(['bash',str(RUNNER),*args,'--repo',str(repo)],env=env,capture_output=True,text=True)
    ROOT.joinpath(name).write_text(p.stdout)
    ROOT.joinpath(name + '.stderr.txt').write_text(p.stderr)
    p.check_returncode()
    return json.loads(p.stdout)

pool_path = INSTANCE / 'candidate-pool.json'
pool = json.loads(pool_path.read_text())
old_pool = json.loads(ROOT.joinpath('candidate-pool-before.json').read_text())
assert pool == old_pool and pool['current_round'] == 22 and pool['selected_candidate_id'] == 'paper-project-entry'
old_audit = json.loads(ROUND.joinpath('audit.json').read_text())
assert old_audit['passed'] and all(digest(ROUND / n) == sha for n,sha in old_audit['sha256'].items())
old_change = json.loads(ROUND.joinpath('change.json').read_text())
assert old_change['candidate_commit'] == OLD == git(WT,'rev-parse','HEAD')
assert git(WT,'diff','--name-only').splitlines() == FILES
assert not git(WT,'ls-files','--others','--exclude-standard')
assert git(PRODUCTION,'rev-parse','HEAD') == old_change['current_production_commit'] and not git(PRODUCTION,'status','--porcelain')
run = cli('run','--part','paper.html','--no-interactive','--json',name='wrapper-resume.json')
assert run['run_id'] == RUN
status = cli('status','--json',name='wrapper-status-before.json')
candidate = next(c for c in status['runs'][RUN]['candidates'] if c['candidate_id'] == 'candidate-001')
assert status['runs'][RUN]['status'] == 'running' and candidate['lifecycle'] == 'allocated' and 'latest_evaluation' not in candidate
repository = json.loads(ROOT.joinpath('github-repository.json').read_text())
assert repository['html_url'] == CODE and repository['full_name'] == 'StringNLPLAB/meta-agent' and repository['private'] is False and repository['archived'] is False

old_text = {n:subprocess.check_output(['git','-C',str(WT),'show',OLD + ':' + n],text=True) for n in FILES}
new_text = {n:WT.joinpath(n).read_text() for n in FILES}
old_hero = '<a class="text-link" data-code-link hidden href="#">Code <span aria-hidden="true">↗</span></a><span class="resource-status" data-code-status>Code · coming soon (under review)</span>'
new_hero = '<a class="text-link" data-code-link href="' + CODE + '" target="_blank" rel="noopener">Code <span aria-hidden="true">↗</span></a>'
old_resource = '<a id="code-link" class="text-link" data-code-link hidden href="#">Code on GitHub <span aria-hidden="true">↗</span></a><span id="code-status" class="resource-status" data-code-status>Code · coming soon (under review)</span>'
new_resource = '<a id="code-link" class="text-link" data-code-link href="' + CODE + '" target="_blank" rel="noopener">Code on GitHub <span aria-hidden="true">↗</span></a>'
expected_home = old_text['index.html'].replace(old_hero,new_hero,1).replace(old_resource,new_resource,1)
readme_anchor = '- **Paper:** [alphaXiv — arXiv:2610.16523](https://www.alphaxiv.org/abs/2610.16523)\n'
llms_anchor = '- Paper (alphaXiv): https://www.alphaxiv.org/abs/2610.16523\n'

class Elements(HTMLParser):
    def __init__(self,text):
        super().__init__()
        self.ids,self.refs,self.anchors,self.code_links,self.h1s = [],[],[],[],0
        self.feed(text)
    def handle_starttag(self,tag,attrs):
        attrs = dict(attrs)
        if 'id' in attrs:
            self.ids.append(attrs['id'])
        self.h1s += tag == 'h1'
        if tag == 'a':
            self.anchors.append(attrs.get('href',''))
            if 'data-code-link' in attrs:
                self.code_links.append(attrs)
        if tag in ['a','link','script','img']:
            ref = attrs.get('href') or attrs.get('src')
            if ref:
                self.refs.append(ref)

pages = {n:Elements(WT.joinpath(n).read_text()) for n in HTML}
errors = []
for n,p in pages.items():
    if len(p.ids) != len(set(p.ids)):
        errors.append(n + ': duplicate IDs')
    for ref in p.refs:
        target = urlparse(ref)
        if target.scheme or target.netloc:
            continue
        path = WT / (unquote(target.path) or n)
        if not path.exists():
            errors.append(n + ': missing ' + ref)
        elif target.fragment and path.suffix == '.html' and target.fragment not in pages[path.name].ids:
            errors.append(n + ': missing fragment ' + ref)
before,after = load_site(str(SITE)),load_site(str(WT))
routing = json.loads(ROUND.joinpath('parents/r18-operations.json').read_text())['operations']
map_limit = json.loads(INSTANCE.joinpath('map.json').read_text())['limits']['max_visible_chars']
frozen = {'map':(INSTANCE / 'map.json','32be06bcafec6c3da9cf8360d86fa8e7154d6d05e1c46e598efd328c2d57973f'),
    'judge':(WRAPPER / 'geo_eval/discovery.py','6bb1498e65e5cf065cc8e03e40007c73c32393e16f85a41d2395db76820613de'),
    'normalizer':(WRAPPER / 'geo_eval/search_api.py','8a2856dd9b69fe4b24c7b315f55ac6c98b7bcbd9063dd1093a11fba3e181d537'),
    'queries':(ROUND / 'queries.txt','f2440c27b9fa7596e902b5bc30a30130e10789564a75f661338742d40876d8ce'),
    'control':(ROUND / 'control/search-matrix.csv','f4c13a905941353d775de225ba6b2e38b2525f1f9116fee2bdaafb85a250a2a4')}
checks = {
    'user_supplied_repository_public_and_exact':repository['html_url'] == CODE and repository['private'] is False,
    'only_four_release_files_changed_since_original_r22':git(WT,'diff','--name-only').splitlines() == FILES,
    'two_static_home_anchors_exactly_updated':new_text['index.html'] == expected_home and old_text['index.html'].count(old_hero) == old_text['index.html'].count(old_resource) == 1,
    'static_links_visible_without_javascript':len(pages['index.html'].code_links) == 2 and all(a['href'] == CODE and 'hidden' not in a and a.get('target') == '_blank' and 'noopener' in a.get('rel','').split() for a in pages['index.html'].code_links),
    'stale_release_status_removed':'coming soon' not in new_text['index.html'].lower() and 'data-code-status' not in new_text['index.html'],
    'configuration_exactly_updated':new_text['site-config.js'] == old_text['site-config.js'].replace('codeUrl: null,  // e.g. "https://github.com/your-org/eau"','codeUrl: "' + CODE + '",',1),
    'readme_only_adds_code_resource':new_text['README.md'] == old_text['README.md'].replace(readme_anchor,readme_anchor + '- **Code:** ' + CODE + '\n',1),
    'llms_only_adds_code_resource':new_text['llms.txt'] == old_text['llms.txt'].replace(llms_anchor,llms_anchor + '- Code: ' + CODE + '\n',1),
    'all_other_original_r22_bytes_unchanged':all(WT.joinpath(n).read_bytes() == subprocess.check_output(['git','-C',str(WT),'show',OLD + ':' + n]) for n in git(WT,'ls-files').splitlines() if n not in FILES),
    'original_paper_relocation_preserved':WT.joinpath('paper.html').read_bytes() == ROUND.joinpath('site/paper.html').read_bytes(),
    'full_scope_vs_r18_is_five_files':git(WT,'diff',old_change['selection_seed_commit'],'--name-only').splitlines() == ALL_FILES,
    'full_scope_vs_live_r21_is_five_files':git(WT,'diff',old_change['current_production_commit'],'--name-only').splitlines() == ALL_FILES,
    'all_heads_metadata_schema_unchanged':all(WT.joinpath(n).read_text().split('</head>',1)[0] == SITE.joinpath(n).read_text().split('</head>',1)[0] for n in HTML),
    'all_nine_alphaxiv_routes_preserved':len(routing) == 9 and all(op['after'] in WT.joinpath(op['node'][5:]).read_text() for op in routing),
    'six_html_alphaxiv_reading_links_preserved':sum(p.anchors.count('https://www.alphaxiv.org/abs/2610.16523') for p in pages.values()) == 6,
    'no_arxiv_reading_link_regression':not any(urlparse(u).netloc in ['arxiv.org','www.arxiv.org'] for p in pages.values() for u in p.anchors),
    'scripts_styles_citations_and_data_untouched':all(WT.joinpath(n).read_bytes() == SITE.joinpath(n).read_bytes() for n in ['script.js','styles.css','CITATION.cff','robots.txt','sitemap.xml']),
    'no_new_hidden_text':all(Counter(after.pages[p].hidden_text.split()) <= Counter(page.hidden_text.split()) for p,page in before.pages.items()),
    'home_visible_text_within_frozen_cap_and_growth_bound':len(after.home.visible_text) <= map_limit and len(after.home.visible_text) <= 1.3*len(before.home.visible_text),
    'other_visible_pages_preserved_vs_original_r22':all(after.pages['/' + n].visible_text == load_site(str(ROUND / 'site')).pages['/' + n].visible_text for n in HTML if n != 'index.html'),
    'jsonld_valid_and_unchanged':all(not p.json_ld_errors for p in after.pages.values()) and all(after.pages[p].json_ld == page.json_ld for p,page in before.pages.items()),
    'links_fragments_ids_valid':not errors,
    'one_h1_per_page':all(p.h1s == 1 for p in pages.values()),
    'frozen_protocol_hashes_unchanged':all(digest(p) == sha for p,sha in frozen.values()),
    'frozen_collection_settings_unchanged':ROUND.joinpath('collection-settings.json').read_bytes() == INSTANCE.joinpath('runs/round-18-alphaxiv-paper-routing/r18-live/collection-settings.json').read_bytes(),
    'original_preparation_archive_intact':all(digest(ROUND / n) == sha for n,sha in old_audit['sha256'].items()),
    'production_unchanged':git(PRODUCTION,'rev-parse','HEAD') == old_change['current_production_commit'] and not git(PRODUCTION,'status','--porcelain'),
    'same_r22_run_no_unpublished_candidate_evaluation':run['run_id'] == RUN and candidate['lifecycle'] == 'allocated' and 'latest_evaluation' not in candidate,
}
assert all(checks.values()),[k for k,v in checks.items() if not v]
write('validation.json',{'checks':checks,'errors':errors,'inner_metric':'not computed','outer_status':'unpublished and unmeasured',
    'visible_home_chars_before':len(before.home.visible_text),'visible_home_chars_after':len(after.home.visible_text),'limit':map_limit,
    'browser_test':'Not run; static anchor attributes and unchanged runtime were checked, not executed in a browser',
    'git_scope_since_original_r22':FILES,'git_scope_vs_r18_and_r21':ALL_FILES})
ROOT.joinpath('code-release.patch').write_text(subprocess.check_output(['git','-C',str(WT),'diff','--unified=3'],text=True))
subprocess.run(['git','-C',str(WT),'diff','--check'],check=True)
subprocess.run(['git','-C',str(WT),'add','--',*FILES],check=True)
subprocess.run(['git','-C',str(WT),'commit','-m','Link released EAU code at StringNLPLAB/meta-agent'],check=True)
commit,tree = git(WT,'rev-parse','HEAD'),git(WT,'rev-parse','HEAD^{tree}')
for name,base in [('candidate.patch',old_change['selection_seed_commit']),('production-to-candidate.patch',old_change['current_production_commit'])]:
    ROOT.joinpath(name).write_text(subprocess.check_output(['git','-C',str(WT),'diff','--unified=3',base,commit],text=True))
for target,name,expected in [(WT,'unpublished-metric-guard.txt',2),(WT.parent / 'seed','historical-control-replay.txt',0)]:
    p = subprocess.run([sys.executable,str(METRIC)],cwd=target,capture_output=True,text=True)
    ROOT.joinpath(name).write_text(p.stdout + p.stderr)
    assert p.returncode == expected and ('No live measurement' in p.stderr if expected == 2 else 'LIVE_PROJECT_CITATIONS=12/60' in p.stdout)

revised = copy.deepcopy(old_change)
revised.update({'revision':'code-release','updated_at':dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds'),
    'candidate_commit':commit,'candidate_tree':tree,'files':ALL_FILES,'graph_nodes':['file:' + n for n in ALL_FILES],
    'previous_candidate_commit':OLD,'previous_candidate_tree':old_change['candidate_tree'],
    'user_requested_code_url':CODE,'user_requested_scope':FILES,'production_changed_files':ALL_FILES,'planned_scope_vs_current_production':ALL_FILES,
    'unchanged_vs_seed':['All website bytes except original paper paragraph placement and four explicit code-release edits','all paper reading alphaXiv routes, scholarly references and research claims','map, query, judge, normalization and settings'],
    'hypothesis':old_change['hypothesis'] + ' This user-requested code-release amendment is an additional coherent bundle; later search results cannot isolate paragraph placement.',
    'production_difference':'Restore best R18 home without the unkept R21 table, retain R22 paragraph relocation, and enable/document the supplied code repository in index/config/README/llms.',
    'deployment_plan':'Separate explicit publication approval required; recheck main, deploy exact full tree and verify all FIVE changed served resources before and after frozen four-engine collection',
    'control_limit':'R18 original 12/60 remains historical only. It predates code release; no causal or one-factor attribution.'})
revised['selection'].update({'deployment':revised['deployment_plan'],'current_production':'R21 unchanged; R22 code-release revision is unpublished and unmeasured'})
write('change.json',revised)
chosen = next(p for p in pool['proposals'] if p['id'] == 'paper-project-entry')
chosen.update({'candidate_commit':commit,'candidate_tree':tree,'files':ALL_FILES,'modules':['paper-authority','homepage-identity','reference-pages','presentation','repository-authority','machine-readable-summary'],
    'scope':'Original R22 paragraph relocation plus user-requested code release: two visible static homepage links, matching codeUrl configuration, README and llms code resources. No unrelated content edits.',
    'hypothesis':revised['hypothesis'],'interpretation':revised['control_limit'],'revision':'code-release','user_requested_code_url':CODE,
    'artifact_dir':'runs/round-22-paper-project-entry/code-release','previous_candidate_commit':OLD,
    'retained_revision':{'candidate_commit':OLD,'candidate_tree':old_change['candidate_tree'],'artifact_dir':'runs/round-22-paper-project-entry','measured':False}})
pool['updated_at'] = revised['updated_at']
pool['policy']['deployment'] = revised['deployment_plan']
pool['policy']['current_production'] = revised['selection']['current_production']
assert pool['history'] == old_pool['history'] and pool['best_observed'] == old_pool['best_observed']
assert [p for p in pool['proposals'] if p['id'] != chosen['id']] == [p for p in old_pool['proposals'] if p['id'] != chosen['id']]
write('candidate-pool-after.json',pool)
config = json.loads(ROUND.joinpath('config.json').read_text())
config['interventions'][0]['nodes'] = revised['graph_nodes']
config['interventions'][0]['hypothesis'] = revised['hypothesis']
write('config.json',config)
cli('geo-graph','--config',str(ROOT / 'config.json'),name='graph-after.json',repo=WT)
status = cli('status','--json',name='wrapper-status-after.json')
assert status['runs'][RUN]['status'] == 'running'
write('original-integrity.json',{'original_audit_sha256':digest(ROUND / 'audit.json'),'all_original_hashes_verified_before_revision':True,
    'preimages':{'CURRENT.json':'code-release/preimages/CURRENT.json','README.md':'code-release/preimages/README.md'},
    'limit':'Root README and CURRENT will point to this revision; verify their historical hashes against preserved preimages. Every other original artifact remains unchanged.'})
ROOT.joinpath('README.md').write_text(f'''# R22 code-release revision

Prepared and validated; not published or measured. Latest candidate:
`{commit}`, tree `{tree}`. Continue the same run `{RUN}` and its allocated
candidate-001. Do not publish the earlier `{OLD}` tree by mistake.

The user supplied {CODE}; the public GitHub API independently confirmed the
exact non-private, non-archived repository. Its contents, training behavior,
license and reproducibility were not audited or executed. No source-repo edits.

Four files change versus the original R22: enable two real, visible static
homepage code anchors, remove both outdated coming-soon labels, set codeUrl,
and add one code resource each in README and llms.txt. Static links no longer
depend on JavaScript. Existing runtime selectors are unchanged. No paper URL,
alphaXiv routing, metadata/schema, research fact, result number or scorer changes.

Original R22 paper-paragraph relocation remains exact. Both the full R18-seed
diff and then-current R21 production diff now span FIVE files: README.md,
index.html, llms.txt, paper.html and site-config.js. The production diff still
removes the unkept R21 table to recover the selected R18 home. Do not inherit
old assumptions that only paper.html or two served files need verification.

All {len(checks)} amendment checks passed; home visible text is
{len(before.home.visible_text)} → {len(after.home.visible_text)} characters under
the locked {map_limit} cap. No inner score or browser execution. The revised
candidate guard refuses scoring (exit 2); original R18 control replays 12/60.
The code release is additional to the original one-relocation experiment, so
later immediate historical-control results cannot isolate paragraph placement
or code-link effects. No matrix was changed and no new search query was run.

All 22 measured historical records, fifteen other proposals, best R18 and the
original unmeasured R22 commit/archive remain preserved. The selected proposal
now points to this revision, not a new round or a fake keep/discard decision.
Root README/CURRENT preimages let the original preparation audit remain
verifiable; all other original hash-covered files are untouched. No rollback,
cleanup, branch pruning or canonical wrapper-state edit was performed.

Production remains R21. Publishing still needs explicit user approval, then
verify the complete exact tree and all FIVE changed served resources before
and after the frozen 15 × GPT web/Codex/Tavily/Exa collection. Keep requires
60/60 valid and strictly over 12 project-domain citations; no memory dimension.
All Python/CLI/validation work used Slurm job {os.environ['SLURM_JOB_ID']}.
''')
names = ['README.md','github-repository.json','change.json','validation.json','code-release.patch','candidate.patch','production-to-candidate.patch',
    'candidate-pool-before.json','candidate-pool-after.json','config.json','graph-after.json','wrapper-resume.json','wrapper-status-before.json','wrapper-status-after.json',
    'unpublished-metric-guard.txt','historical-control-replay.txt','original-integrity.json','update_r22.py','validate.sh','first-validation-attempt.txt']
for n in names:
    content = ROOT.joinpath(n).read_text()
    assert not re.search(r'(?i)tvly-[a-z0-9_-]{16,}|authorization:\s*bearer\s+[a-z0-9_-]{16,}|x-api-key\s*:\s*[a-z0-9_-]{16,}',content),n
    (DEST / n).parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(ROOT / n,DEST / n)
for old,new in [('previous-CURRENT.json','CURRENT.json'),('previous-README.md','README.md')]:
    DEST.joinpath('preimages').mkdir(exist_ok=True)
    shutil.copy2(ROOT / old,DEST / 'preimages' / new)
for n in ALL_FILES + ['method.html','research-context.html']:
    DEST.joinpath('site').mkdir(exist_ok=True)
    shutil.copy2(WT / n,DEST / 'site' / n)
registry = json.loads(ROUND.joinpath('outer-measurements.json').read_text())
registry['measurements'][0]['matrix'] = '../../round-18-alphaxiv-paper-routing/r18-live/search-matrix.csv'
DEST.joinpath('outer-measurements.json').write_text(json.dumps(registry,indent=2) + '\n')
shutil.copy2(ROUND / 'queries.txt',DEST / 'queries.txt')
shutil.copy2(ROUND / 'outer_metric.py',DEST / 'outer_metric.py')
for target,expected in [(WT,2),(WT.parent / 'seed',0)]:
    p = subprocess.run([sys.executable,str(DEST / 'outer_metric.py')],cwd=target,capture_output=True,text=True)
    assert p.returncode == expected
pool_path.write_text(json.dumps(pool,ensure_ascii=False,indent=2) + '\n')
current = {'round':22,'revision':'code-release','artifact_dir':'code-release','state':revised['state'],'published':False,'measured':False,
    'candidate_commit':commit,'candidate_tree':tree,'previous_candidate_commit':OLD,'best_observed_round':18,'current_production_round':21,
    'changed_files_vs_r18_and_r21':ALL_FILES,'original_audit_preimages':'code-release/original-integrity.json'}
ROUND.joinpath('CURRENT.json').write_text(json.dumps(current,indent=2) + '\n')
audit = {'passed':True,'checks':len(checks),'candidate_commit':commit,'candidate_tree':tree,'previous_candidate_commit':OLD,'revision':'code-release',
    'published':False,'measured':False,'control_project_citations':12,'candidate_guard_exit':2,'history_count':22,'proposal_count':16,'other_proposals_preserved':15,
    'slurm_job':os.environ['SLURM_JOB_ID'],'scope_since_original_r22':FILES,'scope_vs_r18_and_r21':ALL_FILES,
    'sha256':{p.relative_to(DEST).as_posix():digest(p) for p in sorted(DEST.rglob('*')) if p.is_file()}}
DEST.joinpath('audit.json').write_text(json.dumps(audit,indent=2) + '\n')
print(json.dumps({k:v for k,v in audit.items() if k != 'sha256'},indent=2))
