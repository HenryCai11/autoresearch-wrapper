"""Validate two visible H1 replacements, without an inner score or live probes."""
import re
import sys
from collections import Counter
from html.parser import HTMLParser
from urllib.parse import unquote, urlparse
from common import *
from geo_eval.site import load_site

assert os.environ.get('SLURM_JOB_ID')
assert not ROOT.joinpath('validation.json').exists(), 'Refuse to validate/recommit twice'
change = json.loads(ROOT.joinpath('change.json').read_text())
run = json.loads(ROOT.joinpath('wrapper-run.json').read_text())
candidate = json.loads(ROOT.joinpath('wrapper-candidate.json').read_text())
worktree = Path(candidate['worktree_path'])
operations = json.loads(ROOT.joinpath('operations.json').read_text())['operations']
source = json.loads(ROOT.joinpath('wording-source.json').read_text())
before = {name:SITE.joinpath(name).read_text() for name in HTML}
after = {name:worktree.joinpath(name).read_text() for name in HTML}
expected = dict(before)
for name,op in zip(FILES,operations):
    assert op['node'] == 'file:' + name and expected[name].count(op['before']) == 1
    expected[name] = expected[name].replace(op['before'],op['after'],1)

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

pages = {name:Elements(text) for name,text in after.items()}
errors = []
for name,page in pages.items():
    if any(count > 1 for count in Counter(page.ids).values()):
        errors.append(name + ': duplicate IDs')
    for ref in page.refs:
        parsed = urlparse(ref)
        if parsed.scheme or parsed.netloc:
            continue
        target = worktree / (unquote(parsed.path) or name)
        if not target.exists():
            errors.append(name + ': missing local path ' + ref)
        elif parsed.fragment and target.suffix == '.html':
            target_page = pages.get(target.name) or Elements(target.read_text())
            if parsed.fragment not in target_page.ids:
                errors.append(name + ': missing fragment ' + ref)
baseline,result = load_site(str(SITE)),load_site(str(worktree))
changed = git(worktree,'diff','--name-only').splitlines()
production_changed = git(worktree,'diff',change['current_production_commit'],'--name-only').splitlines()
limit = json.loads(INSTANCE.joinpath('map.json').read_text())['limits']['max_visible_chars']
frozen = {'knowledge_map_sha256':('geo/instances/eau/map.json','32be06bcafec6c3da9cf8360d86fa8e7154d6d05e1c46e598efd328c2d57973f'),
    'judge_sha256':('geo_eval/discovery.py','6bb1498e65e5cf065cc8e03e40007c73c32393e16f85a41d2395db76820613de'),
    'normalization_sha256':('geo_eval/search_api.py','8a2856dd9b69fe4b24c7b315f55ac6c98b7bcbd9063dd1093a11fba3e181d537')}
routing = json.loads(ROOT.joinpath('sources/r18-operations.json').read_text())['operations']
prior_ops = json.loads(ROOT.joinpath('sources/r19-operations.json').read_text())['operations']
pool = json.loads(INSTANCE.joinpath('candidate-pool.json').read_text())
original = json.loads(ROOT.joinpath('candidate-pool-before.json').read_text())
cli('geo-graph','--config',str(ROOT / 'config.json'),name='graph-after.json',repo=worktree)
graph = json.loads(ROOT.joinpath('graph-after.json').read_text())
nodes = {n['id']:n for n in graph['nodes']}
reversed_pages = dict(after)
for name,op in zip(FILES,operations):
    assert reversed_pages[name].count(op['after']) == 1
    reversed_pages[name] = reversed_pages[name].replace(op['after'],op['before'],1)
reconstructed_production = dict(reversed_pages)
for name,op in zip(HTML,prior_ops):
    assert reconstructed_production[name].count(op['before']) == 1
    reconstructed_production[name] = reconstructed_production[name].replace(op['before'],op['after'],1)
strip_h1 = lambda text:re.sub(r'<h1>.*?</h1>','',text,count=1,flags=re.S)
head = lambda text:text.split('</head>',1)[0]
jsonld = lambda text:re.findall(r'<script type="application/ld\+json">(.*?)</script>',text,re.S)
source_paths = {'r16-operations.json':'round-16-descriptive-section-headings',
    'r18-operations.json':'round-18-alphaxiv-paper-routing','r19-operations.json':'round-19-shared-entity-combination'}
page_key = lambda name:'/' if name == 'index.html' else '/' + name
visible = {name:{'before':len(baseline.pages[page_key(name)].visible_text),'after':len(result.pages[page_key(name)].visible_text)} for name in HTML}
checks = {
    'seed_is_exact_best_r18_not_current_live_r19':git(SITE,'rev-parse','HEAD') == change['selection_seed_commit'] == original['best_observed']['candidate_commit'] and git(SITE,'rev-parse','HEAD^{tree}') == change['selection_seed_tree'] and change['selection_seed_round'] == 18,
    'only_two_authorized_reference_html_files_changed_vs_r18':changed == FILES,
    'production_diff_exactly_four_html_files':production_changed == HTML,
    'exactly_two_manual_heading_replacements':len(operations) == 2 and after == expected and json.loads(ROOT.joinpath('manual-operations.json').read_text())['operations'] == operations,
    'reversing_two_h1s_recovers_all_r18_html_exactly':reversed_pages == before,
    'all_non_h1_bytes_unchanged_vs_r18':all(strip_h1(after[n]) == strip_h1(before[n]) for n in HTML),
    'homepage_and_paper_page_byte_identical_to_best_seed':all(after[n] == before[n] for n in ['index.html','paper.html']),
    'all_head_metadata_and_jsonld_byte_identical_to_r18':all(head(after[n]) == head(before[n]) and jsonld(after[n]) == jsonld(before[n]) for n in HTML),
    'all_four_jsonld_blocks_parse':all(len(jsonld(after[n])) == 1 and isinstance(json.loads(jsonld(after[n])[0]),dict) for n in HTML),
    'no_r19_schema_silently_inherited':all(jsonld(after[n]) != jsonld(PRODUCTION.joinpath(n).read_text()) for n in HTML),
    'reapplying_only_archived_r19_schema_recovers_current_production':all(reconstructed_production[n] == PRODUCTION.joinpath(n).read_text() for n in HTML),
    'method_h1_exact_reuse_of_existing_home_framework_h2':source['method_heading']['source_html'] in before['index.html'] and re.search(r'<h2[^>]*>(.*?)</h2>',source['method_heading']['source_html'],re.S)[1] == re.search(r'<h1>(.*?)</h1>',after['method.html'],re.S)[1],
    'context_h1_uses_existing_lead_phrase':source['context_heading']['source_phrase'] == 'an adaptive training system' and source['context_heading']['source_phrase'] in before['research-context.html'] and operations[1]['after'] == '<h1>EAU as an<br><em>adaptive training system.</em></h1>',
    'all_paragraphs_and_secondary_headings_unchanged':all(re.findall(r'<p\b.*?</p>|<h[2-6]\b.*?</h[2-6]>',after[n],re.S) == re.findall(r'<p\b.*?</p>|<h[2-6]\b.*?</h[2-6]>',before[n],re.S) for n in HTML),
    'all_nine_user_required_r18_alpha_routing_operations_preserved':len(routing) == 9 and all(worktree.joinpath(op['node'][5:]).read_text().count(op['after']) == 1 for op in routing),
    'six_html_paper_anchors_still_alphaxiv':sum(p.anchors.count(ALPHA) for p in pages.values()) == 6,
    'no_html_paper_anchor_reverted_to_arxiv':all(not any(urlparse(ref).netloc in ['arxiv.org','www.arxiv.org'] for ref in p.anchors) for p in pages.values()),
    'homepage_visible_text_unchanged_and_within_limit':result.home.visible_text == baseline.home.visible_text and len(result.home.visible_text) == 6103 <= limit,
    'paper_visible_text_unchanged':result.pages['/paper.html'].visible_text == baseline.pages['/paper.html'].visible_text,
    'reference_page_visible_growth_bounded':all(visible[n]['before'] < visible[n]['after'] < visible[n]['before'] * 1.3 for n in FILES),
    'all_hidden_text_unchanged':all(result.pages[path].hidden_text == p.hidden_text for path,p in baseline.pages.items()),
    'no_jsonld_parser_errors':all(not p.json_ld_errors for p in result.pages.values()),
    'local_links_fragments_and_unique_ids_valid':not errors,
    'exactly_one_h1_per_document':all(p.h1s == Elements(before[n]).h1s == 1 for n,p in pages.items()),
    'scripts_styles_citations_summaries_and_other_assets_unchanged':all(worktree.joinpath(n).read_bytes() == SITE.joinpath(n).read_bytes() for n in ['script.js','styles.css','site-config.js','robots.txt','sitemap.xml','CITATION.cff','README.md','llms.txt','assets/favicon.svg']),
    'archived_wording_and_routing_source_hashes_match':all(digest(ROOT / 'sources' / n) == sha for n,sha in source['source_sha256'].items()),
    'original_source_archives_unchanged':all(digest(INSTANCE / 'runs' / source_paths[n] / 'operations.json') == sha for n,sha in source['source_sha256'].items()),
    'frozen_map_judge_normalizer_unchanged':all(digest(WRAPPER / path) == value for path,value in frozen.values()),
    'frozen_query_list_unchanged':digest(ROOT / 'queries.txt') == 'f2440c27b9fa7596e902b5bc30a30130e10789564a75f661338742d40876d8ce',
    'frozen_engine_settings_unchanged':ROOT.joinpath('collection-settings.json').read_bytes() == INSTANCE.joinpath('runs/round-18-alphaxiv-paper-routing/r18-live/collection-settings.json').read_bytes(),
    'original_r18_control_matrix_not_relabelled_r19':digest(ROOT / 'control/search-matrix.csv') == 'f4c13a905941353d775de225ba6b2e38b2525f1f9116fee2bdaafb85a250a2a4' and json.loads(ROOT.joinpath('outer-measurements.json').read_text())['measurements'][0]['deployed_tree'] == change['selection_seed_tree'],
    'staged_served_r19_bytes_match_unchanged_production':all(ROOT.joinpath('served-r19',n).read_bytes() == PRODUCTION.joinpath(n).read_bytes() for n in HTML),
    'production_checkout_still_original_r19_and_clean':git(PRODUCTION,'rev-parse','HEAD') == change['current_production_commit'] == 'ab6847afc14de3a9067361b071605de711c96337' and not git(PRODUCTION,'status','--porcelain'),
    'all_twenty_history_entries_thirteen_old_proposals_and_best_unchanged':pool['history'] == original['history'] and len(pool['history']) == 20 and all(p in pool['proposals'] for p in original['proposals']) and len(pool['proposals']) == 14 and pool['best_observed'] == original['best_observed'],
    'candidate_has_no_untracked_files':not git(worktree,'ls-files','--others','--exclude-standard'),
    'both_readonly_asset_graph_fingerprints_match_actual_files':all(nodes['file:' + n]['content_sha256'] == digest(worktree / n) and nodes['file:' + n]['operations'] == [] for n in FILES),
}
assert all(checks.values()),[name for name,passed in checks.items() if not passed]
write('validation.json',{'checks':checks,'errors':errors,'inner_score':'not computed','visible_chars':visible,
    'visible_home_chars_before':len(baseline.home.visible_text),'visible_home_chars_after':len(result.home.visible_text),'limit':limit,
    'scope_vs_seed':changed,'scope_vs_current_production':production_changed,
    'browser_test':'Not performed; heading wrapping/visual layout are not claimed as tested',
    'graph_limit':'Both linked files are fingerprinted asset nodes with no text operations; two exact apply_patch edits independently validated',
    **{name:digest(WRAPPER / value[0]) for name,value in frozen.items()}})
ROOT.joinpath('candidate.patch').write_text(subprocess.check_output(['git','-C',str(worktree),'diff','--unified=0'],text=True))
subprocess.run(['git','-C',str(worktree),'diff','--check'],check=True)
subprocess.run(['git','-C',str(worktree),'add','--',*FILES],check=True)
subprocess.run(['git','-C',str(worktree),'commit','-m','R20: use descriptive H1s on method and research-context entry pages'],check=True)
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
    'visible_chars':visible,'status':'R20 validated but unpublished/unmeasured; R19 stays live and R18 best 12/60 remains unchanged'},indent=2))
