"""Replay exactly one retained table on R18, then validate without inner scoring."""
import re
import sys
from collections import Counter
from decimal import Decimal
from html.parser import HTMLParser
from urllib.parse import unquote,urlparse
from common import *
from autoresearch_wrapper.geo import SectionParser
from geo_eval.site import load_site

assert os.environ.get('SLURM_JOB_ID')
assert not ROOT.joinpath('validation.json').exists(), 'Do not recommit a validated candidate'
run = json.loads(ROOT.joinpath('wrapper-run.json').read_text())
change = json.loads(ROOT.joinpath('change.json').read_text())
candidate = json.loads(ROOT.joinpath('wrapper-candidate.json').read_text())
worktree = Path(candidate['worktree_path'])
assert not git(worktree,'status','--porcelain'), 'Candidate must start clean'
config,manifest = str(ROOT / 'config.json'),str(ROOT / 'operations.json')
preview = json.loads(cli('geo-apply','--config',config,'--operations',manifest,name='preview.json',repo=worktree))
applied = json.loads(cli('geo-apply','--config',config,'--operations',manifest,'--apply',name='applied.json',repo=worktree))
cli('geo-graph','--config',config,name='graph-after.json',repo=worktree)
op = json.loads(ROOT.joinpath('operations.json').read_text())['operations'][0]
parent = json.loads(ROOT.joinpath('parents/r14-static-second-backbone-source.json').read_text())
addition = parent['rendered_html']
before,after = SITE.joinpath('index.html').read_text(),worktree.joinpath('index.html').read_text()
javascript = SITE.joinpath('script.js').read_text()

def backbone(key):
    match = re.search(r"  " + key + r": \{\s*label: '([^']+)',\s*rows: \[(.*?)\n    \],\s*\},",javascript,re.S)
    assert match,key
    raw = re.findall(r"\['([^']+)',\s*([0-9.]+),\s*([0-9.]+),\s*([0-9.]+),\s*([0-9.]+)\]",match[2])
    assert len(raw) == 9
    return {'label':match[1],'rows':[[row[0],*[format(Decimal(n),'.3f') for n in row[1:]]] for row in raw]}

def sections(text):
    parser = SectionParser(text)
    parser.feed(text)
    return {key:text[start:end] for key,(start,end) in parser.sections.items()}

class Elements(HTMLParser):
    def __init__(self,text):
        super().__init__()
        self.ids,self.refs,self.anchors,self.h1s = [],[],[],0
        self.feed(text)
    def handle_starttag(self,tag,attrs):
        attrs = dict(attrs)
        if 'id' in attrs:
            self.ids.append(attrs['id'])
        self.h1s += tag == 'h1'
        if tag == 'a':
            self.anchors.append(attrs.get('href',''))
        if tag in ['a','link','script','img']:
            ref = attrs.get('href') or attrs.get('src')
            if ref:
                self.refs.append(ref)

class TableRows(HTMLParser):
    def __init__(self,text):
        super().__init__()
        self.rows,self.row,self.cell = [],None,None
        self.feed(text)
    def handle_starttag(self,tag,attrs):
        if tag == 'tr':
            self.row = []
        elif tag in ['td','th']:
            self.cell = ''
    def handle_data(self,data):
        if self.cell is not None:
            self.cell += data
    def handle_endtag(self,tag):
        if tag in ['td','th']:
            assert self.row is not None and self.cell is not None
            self.row.append(self.cell.strip())
            self.cell = None
        elif tag == 'tr':
            assert self.row is not None
            self.rows.append(self.row)
            self.row = None

second,default = backbone('qwen25'),backbone('qwen3')
new_tbody = re.search(r'<tbody id="second-backbone-table-body">(.*?)</tbody>',after,re.S)[1]
old_tbody = re.search(r'<tbody id="results-table-body">(.*?)</tbody>',after,re.S)[1]
old_sections,new_sections = sections(before),sections(after)
pages = {n:Elements(worktree.joinpath(n).read_text()) for n in HTML}
errors = []
for name,page in pages.items():
    if any(count > 1 for count in Counter(page.ids).values()):
        errors.append(name + ': duplicate IDs')
    for ref in page.refs:
        target = urlparse(ref)
        if target.scheme or target.netloc:
            continue
        path = worktree / (unquote(target.path) or name)
        if not path.exists():
            errors.append(name + ': missing local link ' + ref)
        elif target.fragment and path.suffix == '.html' and target.fragment not in pages[path.name].ids:
            errors.append(name + ': missing fragment ' + ref)
baseline,result = load_site(str(SITE)),load_site(str(worktree))
changed = git(worktree,'diff','--name-only').splitlines()
production_changed = git(worktree,'diff',change['current_production_commit'],'--name-only').splitlines()
limit = json.loads(INSTANCE.joinpath('map.json').read_text())['limits']['max_visible_chars']
frozen = {'knowledge_map_sha256':('geo/instances/eau/map.json','32be06bcafec6c3da9cf8360d86fa8e7154d6d05e1c46e598efd328c2d57973f'),
    'judge_sha256':('geo_eval/discovery.py','6bb1498e65e5cf065cc8e03e40007c73c32393e16f85a41d2395db76820613de'),
    'normalization_sha256':('geo_eval/search_api.py','8a2856dd9b69fe4b24c7b315f55ac6c98b7bcbd9063dd1093a11fba3e181d537')}
source = json.loads(ROOT.joinpath('combination-source.json').read_text())
routing = json.loads(ROOT.joinpath('parents/r18-operations.json').read_text())['operations']
headings = json.loads(ROOT.joinpath('parents/r16-operations.json').read_text())['operations']
old_h1s = json.loads(ROOT.joinpath('parents/r20-operations.json').read_text())['operations']
pool = json.loads(INSTANCE.joinpath('candidate-pool.json').read_text())
original = json.loads(ROOT.joinpath('candidate-pool-before.json').read_text())
graph = json.loads(ROOT.joinpath('graph-after.json').read_text())
nodes = {n['id']:n for n in graph['nodes']}
parent_paths = {'r14-operations.json':'round-14-static-second-backbone-evidence/operations.json',
    'r14-static-second-backbone-source.json':'round-14-static-second-backbone-evidence/static-second-backbone-source.json',
    'r14-change.json':'round-14-static-second-backbone-evidence/change.json','r14-live-summary.json':'round-14-static-second-backbone-evidence/r14-live/summary.json',
    'r20-operations.json':'round-20-descriptive-reference-headings/operations.json','r18-operations.json':'round-18-alphaxiv-paper-routing/operations.json',
    'r16-operations.json':'round-16-descriptive-section-headings/operations.json'}
checks = {
    'only_homepage_changed_vs_exact_r18_best_seed':changed == FILES and git(SITE,'rev-parse','HEAD') == original['best_observed']['candidate_commit'] == change['selection_seed_commit'] and git(SITE,'rev-parse','HEAD^{tree}') == change['selection_seed_tree'],
    'production_diff_exactly_index_method_and_context':production_changed == DEPLOY_FILES,
    'byte_identical_replay_of_final_retained_r14_manifest':ROOT.joinpath('operations.json').read_bytes() == ROOT.joinpath('parents/r14-operations.json').read_bytes() and len(json.loads(ROOT.joinpath('operations.json').read_text())['operations']) == 1,
    'exactly_one_insertion_preserves_every_original_homepage_byte':before.count(op['before']) == 1 and after == before.replace(op['before'],op['after'],1) and op['after'] == addition + op['before'],
    'reversal_removes_only_the_new_table_and_recovers_r18':after.count(addition) == 1 and after.replace(addition,'',1) == before,
    'only_results_named_section_changes':set(old_sections) == set(new_sections) and all(new_sections[k] == v for k,v in old_sections.items() if k != 'results') and old_sections['results'] != new_sections['results'],
    'nine_methods_and_36_values_match_existing_qwen25_js':TableRows(new_tbody).rows == second['rows'] == parent['rows'] and len(second['rows']) == 9 and all(len(r) == 5 for r in second['rows']),
    'all_numeric_values_preserve_three_decimals_and_valid_range':all(re.fullmatch(r'0\.\d{3}|1\.000',n) and Decimal(0) <= Decimal(n) <= Decimal(1) for row in second['rows'] for n in row[1:]),
    'default_qwen3_table_unchanged_and_matches_js':TableRows(old_tbody).rows == default['rows'] and old_tbody == re.search(r'<tbody id="results-table-body">(.*?)</tbody>',before,re.S)[1],
    'model_label_and_independent_caption_explicit':second['label'] == 'Qwen2.5-7B-Instruct' and second['label'] + ' · UserGym and ColBench (static reference)' in addition,
    'default_open_reference_without_script_gating_or_hiding':'id="static-second-backbone-evidence" open>' in addition and all(t not in addition for t in ['<noscript','<script','hidden','display:']),
    'no_new_relative_gains_or_tau2_results':all(t not in addition.lower() for t in ['tau','τ','%']),
    'existing_column_headers_and_styles_reused':parent['headers_html'] == re.search(r'<thead>.*?</thead>',before,re.S)[0] and 'class="result-table-details"' in addition and 'class="table-scroll"' in addition,
    'new_static_ids_are_not_switch_renderer_targets':all('#' + n not in javascript for n in ['second-backbone-table','second-backbone-table-body','second-backbone-caption','static-second-backbone-evidence']),
    'default_switch_buttons_main_charts_and_table_ids_unchanged':all(after.count('id="' + n + '"') == before.count('id="' + n + '"') == 1 for n in ['result-charts','table-caption','results-table-body']) and '<button data-model="qwen3" aria-pressed="true">Qwen3-4B</button><button data-model="qwen25" aria-pressed="false">Qwen2.5-7B</button>' in after and "renderResults('qwen3');" in javascript,
    'retained_r16_headings_preserved':len(headings) == 2 and all(after.count(op['after']) == 1 for op in headings),
    'retained_r17_static_components_and_all_nonresults_bytes_preserved':'id="static-component-reference"' in after and new_sections['framework'] == old_sections['framework'],
    'homepage_h1_unchanged_not_r12_or_r20_replay':re.findall(r'<h1.*?</h1>',after,re.S) == re.findall(r'<h1.*?</h1>',before,re.S),
    'all_support_pages_byte_identical_to_best_r18':all(worktree.joinpath(n).read_bytes() == SITE.joinpath(n).read_bytes() for n in HTML if n != 'index.html'),
    'r20_support_h1_bundle_not_inherited':all(worktree.joinpath(op['node'][5:]).read_text().count(op['before']) == 1 and op['after'] not in worktree.joinpath(op['node'][5:]).read_text() for op in old_h1s),
    'all_heads_metadata_jsonld_and_scholarly_citation_fields_unchanged':all(worktree.joinpath(n).read_text().split('</head>',1)[0] == SITE.joinpath(n).read_text().split('</head>',1)[0] for n in HTML) and new_sections['resources'] == old_sections['resources'],
    'all_nine_required_alphaxiv_routing_operations_preserved':len(routing) == 9 and all(worktree.joinpath(op['node'][5:]).read_text().count(op['after']) == 1 for op in routing),
    'six_html_paper_reading_anchors_still_alphaxiv':sum(p.anchors.count(ALPHA) for p in pages.values()) == 6 and all(not any(urlparse(ref).netloc in ['arxiv.org','www.arxiv.org'] for ref in p.anchors) for p in pages.values()),
    'scripts_styles_config_summaries_citations_and_crawler_files_unchanged':all(worktree.joinpath(n).read_bytes() == SITE.joinpath(n).read_bytes() for n in ['script.js','styles.css','site-config.js','robots.txt','sitemap.xml','CITATION.cff','README.md','llms.txt','assets/favicon.svg']),
    'script_source_hash_matches_original_r14_manifest':digest(worktree / 'script.js') == parent['source_sha256'],
    'no_hidden_text_added':all(result.pages[p].hidden_text == page.hidden_text for p,page in baseline.pages.items()),
    'visible_homepage_within_locked_limit_and_growth_bound':6103 == len(baseline.home.visible_text) < len(result.home.visible_text) <= limit and len(result.home.visible_text) <= 1.3*len(baseline.home.visible_text),
    'all_nonhome_visible_text_unchanged':all(result.pages[p].visible_text == page.visible_text for p,page in baseline.pages.items() if p != '/'),
    'jsonld_valid_and_unchanged':all(not page.json_ld_errors for page in result.pages.values()) and all(result.pages[p].json_ld == page.json_ld for p,page in baseline.pages.items()),
    'local_paths_fragments_and_unique_ids_valid':not errors,
    'one_h1_per_page_preserved':all(p.h1s == Elements(SITE.joinpath(n).read_text()).h1s == 1 for n,p in pages.items()),
    'frozen_map_judge_and_normalizer_unchanged':all(digest(WRAPPER / n) == sha for n,sha in frozen.values()),
    'frozen_queries_settings_and_original_r18_matrix_unchanged':digest(ROOT / 'queries.txt') == 'f2440c27b9fa7596e902b5bc30a30130e10789564a75f661338742d40876d8ce' and ROOT.joinpath('collection-settings.json').read_bytes() == INSTANCE.joinpath('runs/round-18-alphaxiv-paper-routing/r18-live/collection-settings.json').read_bytes() and digest(ROOT / 'control/search-matrix.csv') == 'f4c13a905941353d775de225ba6b2e38b2525f1f9116fee2bdaafb85a250a2a4',
    'parent_archive_copies_and_original_sources_hash_preserved':all(digest(ROOT / 'parents' / n) == sha and digest(INSTANCE / 'runs' / parent_paths[n]) == sha for n,sha in source['parent_artifact_sha256'].items()),
    'current_r20_production_and_served_snapshot_unchanged':git(PRODUCTION,'rev-parse','HEAD') == change['current_production_commit'] and not git(PRODUCTION,'status','--porcelain') and all(ROOT.joinpath('served-r20',n).read_bytes() == PRODUCTION.joinpath(n).read_bytes() for n in HTML),
    'all_old_history_fourteen_proposals_and_best_preserved':pool['history'] == original['history'] and len(pool['history']) == 21 and all(p in pool['proposals'] for p in original['proposals']) and len(pool['proposals']) == 15 and pool['best_observed'] == original['best_observed'],
    'no_untracked_candidate_files':not git(worktree,'ls-files','--others','--exclude-standard'),
    'supported_graph_operation_preview_matches_applied_diff':not preview['applied'] and applied['applied'] and preview['files'] == applied['files'] == FILES and preview['diffs'] == applied['diffs'],
    'graph_home_and_results_fingerprints_match_actual_bytes':nodes['file:index.html']['content_sha256'] == digest(worktree / 'index.html') and nodes['section:results']['content_sha256'] == hashlib.sha256(new_sections['results'].encode()).hexdigest(),
}
assert all(checks.values()),[n for n,passed in checks.items() if not passed]
write('source-verification.json',{'script_sha256':digest(worktree / 'script.js'),'qwen25':second,'default_qwen3':default,
    'row_count':9,'numeric_value_count':36,'matches_exact_parent_source':True,'new_experiments_or_gains':False})
write('validation.json',{'checks':checks,'errors':errors,'inner_score':'not computed','visible_home_chars_before':len(baseline.home.visible_text),
    'visible_home_chars_after':len(result.home.visible_text),'limit':limit,'source_rows':9,'source_numeric_values':36,
    'scope_vs_seed':changed,'scope_vs_current_production':production_changed,
    'browser_test':'Not performed; reused styles and unchanged selectors are structural checks, not browser behavior/layout proof',
    **{n:digest(WRAPPER / value[0]) for n,value in frozen.items()}})
ROOT.joinpath('candidate.patch').write_text(subprocess.check_output(['git','-C',str(worktree),'diff','--unified=0'],text=True))
subprocess.run(['git','-C',str(worktree),'diff','--check'],check=True)
subprocess.run(['git','-C',str(worktree),'add','--',*FILES],check=True)
subprocess.run(['git','-C',str(worktree),'commit','-m','R21: combine retained static second-backbone evidence with best R18'],check=True)
commit,tree = git(worktree,'rev-parse','HEAD'),git(worktree,'rev-parse','HEAD^{tree}')
ROOT.joinpath('production-to-candidate.patch').write_text(subprocess.check_output(['git','-C',str(worktree),'diff','--unified=0',change['current_production_commit'],commit],text=True))
guard = subprocess.run([sys.executable,str(ROOT / 'outer_metric.py')],cwd=worktree,capture_output=True,text=True)
assert guard.returncode == 2 and 'No live measurement' in guard.stderr
ROOT.joinpath('unpublished-metric-guard.txt').write_text(guard.stderr)
change.update({'state':'validated_awaiting_deployment_approval','candidate_commit':commit,'candidate_tree':tree,
    'wrapper_run_id':run['run_id'],'candidate':candidate,'production_changed_files':production_changed})
write('change.json',change)
selected = next(p for p in pool['proposals'] if p['id'] == SELECTED)
selected.update({'status':change['state'],'candidate_commit':commit,'candidate_tree':tree,'wrapper_run_id':run['run_id'],'branch':candidate['branch']})
write('candidate-pool-after.json',pool)
INSTANCE.joinpath('candidate-pool.json').write_text(json.dumps(pool,ensure_ascii=False,indent=2) + '\n')
print(json.dumps({'run_id':run['run_id'],'candidate_commit':commit,'candidate_tree':tree,'checks_passed':len(checks),
    'visible_chars':[len(baseline.home.visible_text),len(result.home.visible_text)],'source_rows':9,'source_numeric_values':36,
    'status':'R21 unmeasured, current R20 production unchanged; best R18 historical 12/60 retained'},indent=2))
