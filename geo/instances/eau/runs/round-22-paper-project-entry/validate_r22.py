"""Validate the main-agent patch; no inner score or unpublished outer eval."""
import re
import sys
from collections import Counter
from html.parser import HTMLParser
from urllib.parse import unquote,urlparse
from common import *
from geo_eval.site import load_site,parse_html

assert os.environ.get('SLURM_JOB_ID')
assert not ROOT.joinpath('validation.json').exists(), 'Do not recommit a validated candidate'
run = json.loads(ROOT.joinpath('wrapper-run.json').read_text())
change = json.loads(ROOT.joinpath('change.json').read_text())
candidate = json.loads(ROOT.joinpath('wrapper-candidate.json').read_text())
worktree = Path(candidate['worktree_path'])
assert git(worktree,'rev-parse','HEAD') == change['selection_seed_commit']
assert git(worktree,'diff','--name-only').splitlines() == FILES
plan = json.loads(ROOT.joinpath('edit-plan.json').read_text())
before,after = [p.joinpath('paper.html').read_text() for p in [SITE,worktree]]
link,anchor = plan['link_paragraph'],plan['identity_anchor']
expected = before.replace(plan['footer_before'],plan['footer_after'],1).replace(plan['identity_before'],plan['identity_after'],1)
footer_marker = '<p class="mini-index">EAU project references</p>\n'
reversed_text = after.replace(plan['identity_after'],plan['identity_before'],1).replace(footer_marker,footer_marker + '    ' + link + '\n',1)

class Elements(HTMLParser):
    def __init__(self,text):
        super().__init__()
        self.ids,self.refs,self.anchors,self.h1s = [],[],[],0
        self.stack,self.errors,self.home_locations = [],[],[]
        self.feed(text)
    def handle_starttag(self,tag,attrs):
        attrs = dict(attrs)
        if 'id' in attrs:
            self.ids.append(attrs['id'])
        self.h1s += tag == 'h1'
        if tag == 'a':
            self.anchors.append(attrs.get('href',''))
            if attrs.get('href') == 'https://eau-meta-agent.github.io/':
                self.home_locations.append([(t,a.get('id'),a.get('class')) for t,a in self.stack])
        if tag in ['a','link','script','img']:
            ref = attrs.get('href') or attrs.get('src')
            if ref:
                self.refs.append(ref)
        if tag not in ['meta','link','img','br','hr','input','source','area','base','col','embed','param','track','wbr']:
            self.stack.append((tag,attrs))
    def handle_endtag(self,tag):
        if self.stack and self.stack[-1][0] == tag:
            self.stack.pop()
        elif tag not in ['meta','link','img','br','hr','input','source','area','base','col','embed','param','track','wbr']:
            self.errors.append('mismatched close ' + tag)

def section(text,key):
    match = re.search(r'<section\b[^>]*\bid="' + key + r'"[^>]*>.*?</section>',text,re.S)
    assert match,key
    return match[0]

pages = {n:Elements(worktree.joinpath(n).read_text()) for n in HTML}
old_paper = Elements(before)
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
old,new = baseline.pages['/paper.html'],result.pages['/paper.html']
changed = git(worktree,'diff','--name-only').splitlines()
production_changed = git(worktree,'diff',change['current_production_commit'],'--name-only').splitlines()
limit = json.loads(INSTANCE.joinpath('map.json').read_text())['limits']['max_visible_chars']
frozen = {'knowledge_map_sha256':('geo/instances/eau/map.json','32be06bcafec6c3da9cf8360d86fa8e7154d6d05e1c46e598efd328c2d57973f'),
    'judge_sha256':('geo_eval/discovery.py','6bb1498e65e5cf065cc8e03e40007c73c32393e16f85a41d2395db76820613de'),
    'normalization_sha256':('geo_eval/search_api.py','8a2856dd9b69fe4b24c7b315f55ac6c98b7bcbd9063dd1093a11fba3e181d537')}
routing = json.loads(ROOT.joinpath('parents/r18-operations.json').read_text())['operations']
pool = json.loads(INSTANCE.joinpath('candidate-pool.json').read_text())
original = json.loads(ROOT.joinpath('candidate-pool-before.json').read_text())
cli('geo-graph','--config',str(ROOT / 'config.json'),name='graph-after.json',repo=worktree)
graphs = [json.loads(ROOT.joinpath(n).read_text()) for n in ['graph-before.json','graph-after.json']]
nodes_before,nodes_after = [{n['id']:n for n in g['nodes']} for g in graphs]
new_locations = pages['paper.html'].home_locations
unchanged_files = git(SITE,'ls-files').splitlines()
checks = {
    'exact_best_r18_seed_not_production_r21':git(SITE,'rev-parse','HEAD') == change['selection_seed_commit'] == original['best_observed']['candidate_commit'] and git(SITE,'rev-parse','HEAD^{tree}') == change['selection_seed_tree'],
    'only_paper_html_changes_vs_seed':changed == FILES,
    'production_diff_exactly_home_and_paper':production_changed == DEPLOY_FILES,
    'exact_single_existing_paragraph_relocation':after == expected and before.count(link) == after.count(link) == 1,
    'inverse_relocation_recovers_every_r18_byte':reversed_text == before,
    'project_paragraph_inside_identity_overview':link in section(after,'identity') and ('section','identity','overview section-pad') in new_locations[0] and ('div',None,'overview-copy') in new_locations[0],
    'original_project_paragraph_was_only_in_footer':len(old_paper.home_locations) == 1 and any(t == 'footer' for t,_,_ in old_paper.home_locations[0]),
    'project_paragraph_not_duplicated_or_in_footer':len(new_locations) == 1 and all(t != 'footer' for t,_,_ in new_locations[0]),
    'identity_copy_and_evaluation_sentence_unchanged':section(after,'identity').replace('\n    ' + link,'',1) == section(before,'identity') and after.count(anchor) == 1,
    'authors_and_reported_evidence_sections_byte_identical':all(section(before,k) == section(after,k) for k in ['authors','evidence']),
    'footer_only_removes_moved_paragraph':after.split('<footer',1)[1] == before.split('<footer',1)[1].replace(plan['footer_before'],plan['footer_after'],1),
    'link_href_counts_unchanged':Counter(pages['paper.html'].anchors) == Counter(old_paper.anchors),
    'all_paper_visible_words_and_length_unchanged':Counter(old.visible_text.split()) == Counter(new.visible_text.split()) and len(old.visible_text) == len(new.visible_text),
    'all_other_tracked_site_files_byte_identical':all(worktree.joinpath(n).read_bytes() == SITE.joinpath(n).read_bytes() for n in unchanged_files if n not in FILES),
    'homepage_exact_r18_without_unkept_r21_table':worktree.joinpath('index.html').read_bytes() == SITE.joinpath('index.html').read_bytes() and 'id="static-second-backbone-evidence"' not in worktree.joinpath('index.html').read_text(),
    'retained_r16_headings_and_r17_static_method_preserved':all(op['after'] in worktree.joinpath('index.html').read_text() for op in json.loads(INSTANCE.joinpath('runs/round-16-descriptive-section-headings/operations.json').read_text())['operations']) and 'id="static-component-reference"' in worktree.joinpath('index.html').read_text(),
    'all_heads_scholarly_citations_and_metadata_unchanged':all(worktree.joinpath(n).read_text().split('</head>',1)[0] == SITE.joinpath(n).read_text().split('</head>',1)[0] for n in HTML),
    'all_nine_alphaxiv_routing_operations_preserved':len(routing) == 9 and all(worktree.joinpath(op['node'][5:]).read_text().count(op['after']) == 1 for op in routing),
    'six_html_reading_anchors_still_alphaxiv':sum(p.anchors.count(ALPHA) for p in pages.values()) == 6 and all(not any(urlparse(ref).netloc in ['arxiv.org','www.arxiv.org'] for ref in p.anchors) for p in pages.values()),
    'no_hidden_text_added':all(result.pages[p].hidden_text == page.hidden_text for p,page in baseline.pages.items()),
    'homepage_visible_text_unchanged_and_within_bound':len(baseline.home.visible_text) == len(result.home.visible_text) == 6103 and len(result.home.visible_text) <= limit,
    'all_other_page_visible_text_unchanged':all(result.pages[p].visible_text == page.visible_text for p,page in baseline.pages.items() if p != '/paper.html'),
    'all_jsonld_valid_and_unchanged':all(not p.json_ld_errors for p in result.pages.values()) and all(result.pages[p].json_ld == page.json_ld for p,page in baseline.pages.items()),
    'local_links_fragments_unique_ids_valid':not errors,
    'paper_html_tags_balanced':not pages['paper.html'].errors and not pages['paper.html'].stack,
    'one_h1_per_page_preserved':all(p.h1s == Elements(SITE.joinpath(n).read_text()).h1s == 1 for n,p in pages.items()),
    'all_frozen_map_judge_normalizer_hashes_unchanged':all(digest(WRAPPER / n) == sha for n,sha in frozen.values()),
    'frozen_queries_and_collection_settings_unchanged':digest(ROOT / 'queries.txt') == 'f2440c27b9fa7596e902b5bc30a30130e10789564a75f661338742d40876d8ce' and ROOT.joinpath('collection-settings.json').read_bytes() == INSTANCE.joinpath('runs/round-18-alphaxiv-paper-routing/r18-live/collection-settings.json').read_bytes(),
    'original_r18_control_matrix_not_r21':digest(ROOT / 'control/search-matrix.csv') == 'f4c13a905941353d775de225ba6b2e38b2525f1f9116fee2bdaafb85a250a2a4',
    'current_production_and_served_snapshot_unchanged':git(PRODUCTION,'rev-parse','HEAD') == change['current_production_commit'] and not git(PRODUCTION,'status','--porcelain') and all(ROOT.joinpath('served-r21',n).read_bytes() == PRODUCTION.joinpath(n).read_bytes() for n in HTML),
    'all_22_history_15_old_proposals_and_best_preserved':pool['history'] == original['history'] and len(pool['history']) == 22 and all(p in pool['proposals'] for p in original['proposals']) and len(pool['proposals']) == 16 and pool['best_observed'] == original['best_observed'],
    'no_untracked_candidate_files':not git(worktree,'ls-files','--others','--exclude-standard'),
    'support_asset_no_claimed_geo_apply_operation':nodes_before['file:paper.html']['kind'] == 'asset' and nodes_before['file:paper.html']['operations'] == nodes_after['file:paper.html']['operations'] == [],
    'graph_paper_fingerprint_matches_and_is_only_changed_node':nodes_after['file:paper.html']['content_sha256'] == digest(worktree / 'paper.html') and [k for k,n in nodes_before.items() if n.get('content_sha256') != nodes_after[k].get('content_sha256')] == ['file:paper.html'],
}
assert all(checks.values()),[n for n,passed in checks.items() if not passed]
write('source-verification.json',{'source':'Existing R18 and served R21 paper.html paragraph','source_sha256':digest(SITE / 'paper.html'),
    'paragraph':link,'new_facts':False,'new_words':False,'new_links':False,'link_state_before':'present','link_state_after':'present; placement only',
    'old_location':'reference footer','new_location':'identity overview-copy','source_cells':3,'source_platform':'exa-search',
    'limit':'Saved snippet omission does not establish a cause or retrieval lift'})
write('validation.json',{'checks':checks,'errors':errors,'inner_score':'not computed',
    'visible_home_chars_before':len(baseline.home.visible_text),'visible_home_chars_after':len(result.home.visible_text),
    'visible_paper_chars_before':len(old.visible_text),'visible_paper_chars_after':len(new.visible_text),'limit':limit,
    'scope_vs_seed':changed,'scope_vs_current_production':production_changed,'browser_test':'Not performed; structural validity and unchanged classes do not prove rendered layout',
    **{n:digest(WRAPPER / value[0]) for n,value in frozen.items()}})
ROOT.joinpath('candidate.patch').write_text(subprocess.check_output(['git','-C',str(worktree),'diff','--unified=0'],text=True))
subprocess.run(['git','-C',str(worktree),'diff','--check'],check=True)
subprocess.run(['git','-C',str(worktree),'add','--',*FILES],check=True)
subprocess.run(['git','-C',str(worktree),'commit','-m','R22: place existing official project link beside paper identity'],check=True)
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
    'home_chars':[len(baseline.home.visible_text),len(result.home.visible_text)],'paper_chars':[len(old.visible_text),len(new.visible_text)],
    'status':'R22 unpublished and unmeasured; production R21 unchanged; best R18 12/60 retained'},indent=2))
