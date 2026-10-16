"""Validate the metadata-only intervention without assigning an outer score."""
import hashlib
import html
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

from geo_eval.site import load_site

ROOT = Path(__file__).resolve().parent
WRAPPER = Path('/project/aip-xiye17/henrycai/autoresearch-wrapper')
INSTANCE = WRAPPER / 'geo/instances/eau'
SITE = Path('/scratch/henrycai/eau-r10-20261016')
FILES = ['index.html', 'method.html', 'paper.html', 'research-context.html']
LD = re.compile(r'<script\s+type="application/ld\+json">\s*(.*?)\s*</script>', re.S)
BASE_URL = 'https://eau-meta-agent.github.io/'
ARTICLE_ID = BASE_URL + '#paper'
candidate = json.loads(ROOT.joinpath('wrapper-candidate.json').read_text())
worktree = Path(candidate['worktree_path'])
change = json.loads(ROOT.joinpath('change.json').read_text())
expected = json.loads(ROOT.joinpath('schema-after.json').read_text())
old = json.loads(ROOT.joinpath('schema-before.json').read_text())
assert subprocess.check_output(['git', '-C', str(SITE), 'rev-parse', 'HEAD'], text=True).strip() == change['base_production_commit']
assert not subprocess.check_output(['git', '-C', str(SITE), 'status', '--porcelain'], text=True).strip()


def write(name, value):
    ROOT.joinpath(name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


sources = {name: SITE.joinpath(name).read_text() for name in FILES}
edited = {name: worktree.joinpath(name).read_text() for name in FILES}
graphs = {name: json.loads(LD.search(edited[name]).group(1)) for name in FILES}
pages = {name: [n for n in graph['@graph'] if n['@type'] == 'WebPage'] for name, graph in graphs.items()}
articles = {name: [n for n in graph['@graph'] if n['@type'] == 'ScholarlyArticle'] for name, graph in graphs.items()}
node_ids = {n['@id'] for graph in graphs.values() for n in graph['@graph']}


def all_refs(value):
    if isinstance(value, dict):
        for key, item in value.items():
            if key == '@id':
                yield item
            else:
                yield from all_refs(item)
    elif isinstance(value, list):
        for item in value:
            yield from all_refs(item)


base_site, candidate_site = load_site(str(SITE)), load_site(str(worktree))
paths = {name: '/' if name == 'index.html' else '/' + name for name in FILES}
changed = subprocess.check_output(['git', '-C', str(worktree), 'diff', '--name-only'], text=True).splitlines()
untracked = subprocess.check_output(['git', '-C', str(worktree), 'ls-files', '--others', '--exclude-standard'], text=True).splitlines()
article = articles['index.html'][0]
original_home = {k: v for k, v in old['index.html'].items() if k != '@context'}
limit = json.loads(INSTANCE.joinpath('map.json').read_text())['limits']['max_visible_chars']
frozen = {
    'knowledge_map_sha256': ('geo/instances/eau/map.json', '32be06bcafec6c3da9cf8360d86fa8e7154d6d05e1c46e598efd328c2d57973f'),
    'judge_sha256': ('geo_eval/discovery.py', '6bb1498e65e5cf065cc8e03e40007c73c32393e16f85a41d2395db76820613de'),
    'normalization_sha256': ('geo_eval/search_api.py', '8a2856dd9b69fe4b24c7b315f55ac6c98b7bcbd9063dd1093a11fba3e181d537'),
}
checks = {
    'exact_four_file_scope_and_no_untracked_files': changed == sorted(FILES) and not untracked,
    'exactly_one_jsonld_block_per_page': all(len(LD.findall(source)) == 1 for source in edited.values()),
    'only_jsonld_changed': all(LD.sub('<JSON-LD>', sources[name]) == LD.sub('<JSON-LD>', edited[name]) for name in FILES),
    'all_body_bytes_unchanged_including_r9_static_results': all(sources[name].split('</head>', 1)[1] == edited[name].split('</head>', 1)[1] for name in FILES),
    'visible_text_and_hidden_text_unchanged': all(candidate_site.pages[path].visible_text == page.visible_text and candidate_site.pages[path].hidden_text == page.hidden_text for path, page in base_site.pages.items()),
    'non_jsonld_metadata_titles_canonicals_links_unchanged': all((candidate_site.pages[path].meta, candidate_site.pages[path].title, candidate_site.pages[path].canonical, candidate_site.pages[path].links) == (page.meta, page.title, page.canonical, page.links) for path, page in base_site.pages.items()),
    'all_jsonld_parses': all(not page.json_ld_errors for page in candidate_site.pages.values()),
    'schema_objects_match_prepared_contract': graphs == expected,
    'one_article_and_one_webpage_per_document': all(len(pages[name]) == len(articles[name]) == 1 and len(graphs[name]['@graph']) == 2 for name in FILES),
    'one_identical_scholarly_entity_across_four_documents': all(value[0] == article for value in articles.values()) and article['@id'] == ARTICLE_ID,
    'four_distinct_webpage_ids_with_own_canonical_urls': len({value[0]['@id'] for value in pages.values()}) == 4 and all(pages[name][0]['url'] == base_site.pages[paths[name]].canonical and pages[name][0]['@id'] == pages[name][0]['url'] + '#webpage' for name in FILES),
    'webpage_names_equal_document_head_titles_not_svg_titles': all(pages[name][0]['name'] == html.unescape(re.search(r'<title>(.*?)</title>', sources[name].split('</head>', 1)[0], re.S).group(1)) for name in FILES),
    'webpage_mainentity_points_to_shared_article': all(value[0]['mainEntity'] == {'@id': ARTICLE_ID} for value in pages.values()),
    'article_mainentityofpage_points_to_canonical_homepage': article['mainEntityOfPage'] == {'@id': BASE_URL + '#webpage'},
    'all_entity_references_resolve_across_document_set': all(ref in node_ids and urlparse(ref).scheme == 'https' and urlparse(ref).netloc == 'eau-meta-agent.github.io' for graph in graphs.values() for ref in all_refs(graph)),
    'all_original_home_article_facts_preserved': all(article[k] == v for k, v in original_home.items()),
    'only_existing_paper_date_and_headline_added_to_article': set(article) == set(original_home) | {'@id', 'mainEntityOfPage', 'headline', 'datePublished'} and article['datePublished'] == old['paper.html']['datePublished'] and article['headline'] == old['paper.html']['headline'],
    'page_descriptions_topics_keywords_preserved': all(pages[name][0]['description'] == old[name]['description'] and all(pages[name][0].get(field) == old[name].get(field) for field in ['about', 'keywords']) for name in FILES),
    'existing_visible_text_limit_respected': len(candidate_site.home.visible_text) <= limit,
    'frozen_map_judge_and_normalizer_unchanged': all(digest(WRAPPER / path) == value for path, value in frozen.values()),
    'query_set_unchanged': digest(ROOT / 'queries.txt') == 'f2440c27b9fa7596e902b5bc30a30130e10789564a75f661338742d40876d8ce',
}
write('schema-contract.json', {'article_id': ARTICLE_ID, 'article': article,
    'webpages': {name: value[0] for name, value in pages.items()}, 'unique_declared_nodes': sorted(node_ids),
    'test_scope': 'Local JSON syntax, entity/reference contracts and source-preservation checks; not full RDF expansion or a search-engine rich-result validator.'})
validation = {'checks': checks, 'inner_score': 'not computed',
    'visible_home_chars_before': len(base_site.home.visible_text), 'visible_home_chars_after': len(candidate_site.home.visible_text),
    'limit': limit, 'files': {name: {'before_sha256': digest(SITE / name), 'after_sha256': digest(worktree / name)} for name in FILES},
    **{name: digest(WRAPPER / value[0]) for name, value in frozen.items()}}
write('validation.json', validation)
assert all(checks.values()), [name for name, passed in checks.items() if not passed]
environment = os.environ.copy()
environment.pop('PYTHONPATH', None)
graph = subprocess.run(['bash', str(WRAPPER / 'skills/autoresearch-wrapper-run/run.sh'), 'geo-graph', '--repo', str(worktree), '--config', str(ROOT / 'config.json')], env=environment, capture_output=True, text=True, check=True)
ROOT.joinpath('graph-after.json').write_text(graph.stdout)
write('edit-mechanism.json', {'homepage': 'geo-apply replace_text on meta:schema',
    'support_pages': 'Exact generated schema-only patch applied with the agent apply_patch tool',
    'reason': 'Current geo-apply exposes linked HTML assets but does not permit replace_text on them; no wrapper-core mutation or bypass of canonical run state.',
    'scope': FILES, 'verified': 'Only one JSON-LD block per page differs; all non-JSON-LD bytes unchanged.'})
ROOT.joinpath('candidate.patch').write_text(subprocess.check_output(['git', '-C', str(worktree), 'diff', '--unified=0'], text=True))
subprocess.run(['git', '-C', str(worktree), 'diff', '--check'], check=True)
subprocess.run(['git', '-C', str(worktree), 'add', '--', *FILES], check=True)
subprocess.run(['git', '-C', str(worktree), 'commit', '-m', 'R10: unify scholarly identity across project reference pages'], check=True)
commit = subprocess.check_output(['git', '-C', str(worktree), 'rev-parse', 'HEAD'], text=True).strip()
tree = subprocess.check_output(['git', '-C', str(worktree), 'rev-parse', 'HEAD^{tree}'], text=True).strip()
guard = subprocess.run([sys.executable, str(ROOT / 'outer_metric.py')], cwd=worktree, capture_output=True, text=True)
assert guard.returncode == 2 and 'No live measurement' in guard.stderr
ROOT.joinpath('unpublished-metric-guard.txt').write_text(guard.stderr)
change.update({'state': 'validated_awaiting_deployment_approval', 'candidate_commit': commit, 'candidate_tree': tree,
               'wrapper_run_id': json.loads(ROOT.joinpath('wrapper-run.json').read_text())['run_id'], 'candidate': candidate})
write('change.json', change)
pool_path = INSTANCE / 'candidate-pool.json'
pool = json.loads(pool_path.read_text())
assert pool['selected_candidate_id'] == 'shared-scholarly-entity' and pool['current_round'] == 10
selected = next(item for item in pool['proposals'] if item['id'] == pool['selected_candidate_id'])
selected.update({'status': change['state'], 'candidate_commit': commit, 'candidate_tree': tree,
                 'wrapper_run_id': change['wrapper_run_id'], 'branch': candidate['branch'], 'retain_for_combinations': True})
write('candidate-pool-after.json', pool)
pool_path.write_text(json.dumps(pool, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({'run_id': change['wrapper_run_id'], 'candidate_commit': commit, 'candidate_tree': tree,
                  'validation_checks': len(checks), 'all_passed': True, 'outer_metric': 'unmeasured until approved deployment'}, indent=2))
