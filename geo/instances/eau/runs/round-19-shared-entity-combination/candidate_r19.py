"""Validate exact final R10 metadata on R18 without computing an inner score."""
import re
import sys
from collections import Counter
from html.parser import HTMLParser
from urllib.parse import unquote, urlparse
from common import *
from geo_eval.site import load_site

assert os.environ.get('SLURM_JOB_ID')
assert not ROOT.joinpath('validation.json').exists(), 'Do not recommit a validated candidate'
change = json.loads(ROOT.joinpath('change.json').read_text())
run = json.loads(ROOT.joinpath('wrapper-run.json').read_text())
candidate = json.loads(ROOT.joinpath('wrapper-candidate.json').read_text())
worktree = Path(candidate['worktree_path'])
operations = json.loads(ROOT.joinpath('operations.json').read_text())['operations']
manifest = json.loads(ROOT.joinpath('combination-source.json').read_text())
contract = json.loads(ROOT.joinpath('parents/r10-schema-contract.json').read_text())
old_payloads = json.loads(ROOT.joinpath('parents/r10-schema-before.json').read_text())
final_payloads = json.loads(ROOT.joinpath('parents/r10-schema-after.json').read_text())
pattern = r'<script type="application/ld\+json">.*?</script>'
before = {name:SITE.joinpath(name).read_text() for name in FILES}
after = {name:worktree.joinpath(name).read_text() for name in FILES}
expected = dict(before)
for name,op in zip(FILES,operations):
    assert expected[name].count(op['before']) == 1
    expected[name] = expected[name].replace(op['before'],op['after'],1)
payloads = {name:json.loads(re.findall(pattern,text,re.S)[0].split('>',1)[1].rsplit('</script>',1)[0]) for name,text in after.items()}
articles = {name:next(n for n in value['@graph'] if n['@type'] == 'ScholarlyArticle') for name,value in payloads.items()}
webpages = {name:next(n for n in value['@graph'] if n['@type'] == 'WebPage') for name,value in payloads.items()}

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
        elif parsed.fragment and target.suffix == '.html' and parsed.fragment not in pages[target.name].ids:
            errors.append(name + ': missing fragment ' + ref)
baseline,result = load_site(str(SITE)),load_site(str(worktree))
changed = git(worktree,'diff','--name-only').splitlines()
production_changed = git(worktree,'diff',change['current_production_commit'],'--name-only').splitlines()
limit = json.loads(INSTANCE.joinpath('map.json').read_text())['limits']['max_visible_chars']
frozen = {'knowledge_map_sha256':('geo/instances/eau/map.json','32be06bcafec6c3da9cf8360d86fa8e7154d6d05e1c46e598efd328c2d57973f'),
    'judge_sha256':('geo_eval/discovery.py','6bb1498e65e5cf065cc8e03e40007c73c32393e16f85a41d2395db76820613de'),
    'normalization_sha256':('geo_eval/search_api.py','8a2856dd9b69fe4b24c7b315f55ac6c98b7bcbd9063dd1093a11fba3e181d537')}
routing_ops = json.loads(ROOT.joinpath('parents/r18-operations.json').read_text())['operations']
pool = json.loads(INSTANCE.joinpath('candidate-pool.json').read_text())
original = json.loads(ROOT.joinpath('candidate-pool-before.json').read_text())
cli('geo-graph','--config',str(ROOT / 'config.json'),name='graph-after.json',repo=worktree)
graph = json.loads(ROOT.joinpath('graph-after.json').read_text())
schema_node = next(n for n in graph['nodes'] if n['id'] == 'meta:schema')
head_title = lambda text: re.search(r'<title>([^<]+)</title>',text.split('</head>',1)[0])[1]
strip_schema = lambda text: re.sub(pattern,'',text,count=1,flags=re.S)
checks = {
    'only_four_authorized_html_files_changed':changed == FILES and production_changed == FILES,
    'exactly_four_archived_schema_replacements':len(operations) == 4 and after == expected,
    'all_non_jsonld_bytes_unchanged':all(strip_schema(after[n]) == strip_schema(before[n]) for n in FILES),
    'all_body_html_byte_unchanged':all(after[n].split('<body>',1)[1] == before[n].split('<body>',1)[1] for n in FILES),
    'reversing_only_schema_blocks_recovers_r18_exactly':all(after[n].count(op['after']) == 1 and after[n].replace(op['after'],op['before'],1) == before[n] for n,op in zip(FILES,operations)),
    'replays_final_measured_r10_payloads_not_a_draft':payloads == final_payloads,
    'one_page_and_one_article_node_per_document':all(len(p['@graph']) == 2 and sorted(n['@type'] for n in p['@graph']) == ['ScholarlyArticle','WebPage'] for p in payloads.values()),
    'all_four_shared_articles_identical_to_parent_contract':all(article == contract['article'] for article in articles.values()),
    'one_shared_absolute_paper_identifier':{a['@id'] for a in articles.values()} == {contract['article_id']} and contract['article_id'] == 'https://eau-meta-agent.github.io/#paper',
    'all_four_main_entities_reference_shared_paper':all(p['mainEntity'] == {'@id':contract['article_id']} for p in webpages.values()),
    'four_distinct_absolute_webpage_identifiers':len({p['@id'] for p in webpages.values()}) == 4 and all(p['@id'] == p['url'] + '#webpage' for p in webpages.values()),
    'webpage_fields_match_final_archived_contract':all(p == contract['webpages'][name] for name,p in webpages.items()),
    'webpage_names_match_actual_head_titles_not_svg_titles':all(p['name'] == head_title(after[name]) for name,p in webpages.items()),
    'page_specific_descriptions_topics_and_keywords_preserved':all(all(p.get(k) == old_payloads[name].get(k) for k in ['description','about','keywords'] if k in old_payloads[name]) for name,p in webpages.items()),
    'article_author_facts_equal_existing_homepage_authors':all(a['author'] == old_payloads['index.html']['author'] for a in articles.values()),
    'article_title_year_and_arxiv_identity_from_existing_data':all(a['name'] == old_payloads['paper.html']['name'] and a['datePublished'] == old_payloads['paper.html']['datePublished'] and a['identifier'] == old_payloads['index.html']['identifier'] and a['sameAs'] == old_payloads['index.html']['sameAs'] for a in articles.values()),
    'all_article_urls_use_existing_canonical_project_home':all(a['url'] == 'https://eau-meta-agent.github.io/' and a['mainEntityOfPage'] == {'@id':'https://eau-meta-agent.github.io/#webpage'} for a in articles.values()),
    'all_nine_user_required_r18_routing_operations_preserved':len(routing_ops) == 9 and all(worktree.joinpath(op['node'][5:]).read_text().count(op['after']) == 1 for op in routing_ops),
    'all_six_html_paper_anchors_still_alphaxiv':sum(p.anchors.count(ALPHA) for p in pages.values()) == 6,
    'no_html_paper_anchor_reverted_to_arxiv':all(not any(urlparse(ref).netloc in ['arxiv.org','www.arxiv.org'] for ref in p.anchors) for p in pages.values()),
    'all_pages_visible_text_byte_unchanged':all(result.pages[path].visible_text == p.visible_text for path,p in baseline.pages.items()),
    'all_hidden_text_unchanged':all(result.pages[path].hidden_text == p.hidden_text for path,p in baseline.pages.items()),
    'visible_homepage_within_existing_limit':len(result.home.visible_text) == len(baseline.home.visible_text) <= limit,
    'jsonld_parses_without_errors':all(not p.json_ld_errors for p in result.pages.values()),
    'local_links_fragments_and_unique_ids_valid':not errors,
    'one_h1_per_page_unchanged':all(p.h1s == Elements(before[name]).h1s == 1 for name,p in pages.items()),
    'all_other_files_scripts_styles_citations_and_machine_summaries_unchanged':all(worktree.joinpath(name).read_bytes() == SITE.joinpath(name).read_bytes() for name in ['script.js','styles.css','site-config.js','robots.txt','sitemap.xml','CITATION.cff','README.md','llms.txt','assets/favicon.svg']),
    'non_jsonld_bibtex_pdf_and_citation_fields_retained':all(strip_schema(after[n]) == strip_schema(before[n]) for n in ['index.html','paper.html']),
    'archived_parent_artifact_hashes_preserved':all(digest(ROOT / 'parents' / name) == value for name,value in manifest['parent_artifact_sha256'].items()),
    'original_r10_and_r18_parent_archives_unchanged':all(digest(INSTANCE / 'runs/round-10-shared-scholarly-entity' / name.removeprefix('r10-')) == value for name,value in manifest['parent_artifact_sha256'].items() if name.startswith('r10-')) and digest(INSTANCE / 'runs/round-18-alphaxiv-paper-routing/operations.json') == manifest['parent_artifact_sha256']['r18-operations.json'],
    'frozen_map_judge_and_normalizer_unchanged':all(digest(WRAPPER / path) == value for path,value in frozen.values()),
    'frozen_queries_unchanged':digest(ROOT / 'queries.txt') == 'f2440c27b9fa7596e902b5bc30a30130e10789564a75f661338742d40876d8ce',
    'frozen_engine_settings_and_r18_matrix_unchanged':ROOT.joinpath('collection-settings.json').read_bytes() == INSTANCE.joinpath('runs/round-18-alphaxiv-paper-routing/r18-live/collection-settings.json').read_bytes() and digest(ROOT / 'control/search-matrix.csv') == 'f4c13a905941353d775de225ba6b2e38b2525f1f9116fee2bdaafb85a250a2a4',
    'current_served_r18_source_matches_seed':all(ROOT.joinpath('served-r18',n).read_bytes() == SITE.joinpath(n).read_bytes() for n in FILES),
    'production_r18_checkout_unchanged':git(PRODUCTION,'rev-parse','HEAD') == change['current_production_commit'] and not git(PRODUCTION,'status','--porcelain'),
    'all_old_history_proposals_and_best_unchanged':pool['history'] == original['history'] and all(p in pool['proposals'] for p in original['proposals']) and pool['best_observed'] == original['best_observed'],
    'no_untracked_candidate_files':not git(worktree,'ls-files','--others','--exclude-standard'),
    'supported_schema_graph_fingerprint_matches_actual_block':schema_node['content_sha256'] == hashlib.sha256(operations[0]['after'].encode()).hexdigest(),
}
assert all(checks.values()),[name for name,passed in checks.items() if not passed]
write('schema-after.json',payloads)
write('validation.json',{'checks':checks,'errors':errors,'inner_score':'not computed',
    'visible_home_chars_before':len(baseline.home.visible_text),'visible_home_chars_after':len(result.home.visible_text),
    'limit':limit,'scope_vs_seed':changed,'scope_vs_current_production':production_changed,
    'browser_test':'not performed; all body HTML/scripts/styles byte-unchanged, but browser behavior is not claimed as tested',
    'graph_limit':'Homepage metadata fingerprint only; three support-file operations independently validated',
    **{name:digest(WRAPPER / value[0]) for name,value in frozen.items()}})
ROOT.joinpath('candidate.patch').write_text(subprocess.check_output(['git','-C',str(worktree),'diff','--unified=0'],text=True))
subprocess.run(['git','-C',str(worktree),'diff','--check'],check=True)
subprocess.run(['git','-C',str(worktree),'add','--',*FILES],check=True)
subprocess.run(['git','-C',str(worktree),'commit','-m','R19: combine exact retained shared-paper metadata with measured R18 routes'],check=True)
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
    'visible_chars':[len(baseline.home.visible_text),len(result.home.visible_text)],
    'status':'Unmeasured R19 combination; current R18 production and best 12/60 control unchanged'},indent=2))
