"""Validate exactly nine URL/label replacements; no live or inner scoring."""
import re
import sys
from collections import Counter
from html.parser import HTMLParser
from urllib.parse import unquote, urlparse
from common import *
from autoresearch_wrapper.geo import SectionParser
from geo_eval.site import load_site

assert os.environ.get('SLURM_JOB_ID')
assert not ROOT.joinpath('validation.json').exists(), 'Do not revalidate or recommit an archived candidate'
run = json.loads(ROOT.joinpath('wrapper-run.json').read_text())
change = json.loads(ROOT.joinpath('change.json').read_text())
candidate = json.loads(ROOT.joinpath('wrapper-candidate.json').read_text())
worktree = Path(candidate['worktree_path'])
operations = json.loads(ROOT.joinpath('operations.json').read_text())['operations']
expected = {name: SITE.joinpath(name).read_text() for name in FILES}
for op in operations:
    name = op['node'][5:]
    assert expected[name].count(op['before']) == 1, name
    expected[name] = expected[name].replace(op['before'], op['after'], 1)
cli('geo-graph', '--config', str(ROOT / 'config.json'), name='graph-after.json', repo=worktree)

class Elements(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.ids, self.refs, self.anchors, self.h1s = [], [], [], 0
        self.feed(text)
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if 'id' in attrs:
            self.ids.append(attrs['id'])
        self.h1s += tag == 'h1'
        if tag == 'a':
            self.anchors.append(attrs.get('href', ''))
        if tag in ['a', 'link', 'script', 'img']:
            ref = attrs.get('href') or attrs.get('src')
            if ref:
                self.refs.append(ref)

def sections(text):
    parser = SectionParser(text)
    parser.feed(text)
    return {key: text[span[0]:span[1]] for key, span in parser.sections.items()}

pages = {path.name: Elements(path.read_text()) for path in worktree.glob('*.html')}
errors = []
for name, page in pages.items():
    if any(count > 1 for count in Counter(page.ids).values()):
        errors.append(f'{name}: duplicate IDs')
    for ref in page.refs:
        target = urlparse(ref)
        if target.scheme or target.netloc:
            continue
        path = worktree / (unquote(target.path) or name)
        if not path.exists():
            errors.append(f'{name}: missing local link {ref}')
        elif target.fragment and path.suffix == '.html' and target.fragment not in pages[path.name].ids:
            errors.append(f'{name}: missing fragment {ref}')

source, edited = SITE.joinpath('index.html').read_text(), worktree.joinpath('index.html').read_text()
old_sections, new_sections = sections(source), sections(edited)
baseline, result = load_site(str(SITE)), load_site(str(worktree))
changed = git(worktree, 'diff', '--name-only').splitlines()
production_changed = git(worktree, 'diff', change['current_production_commit'], '--name-only').splitlines()
limit = json.loads(INSTANCE.joinpath('map.json').read_text())['limits']['max_visible_chars']
frozen = {'knowledge_map_sha256': ('geo/instances/eau/map.json', '32be06bcafec6c3da9cf8360d86fa8e7154d6d05e1c46e598efd328c2d57973f'),
    'judge_sha256': ('geo_eval/discovery.py', '6bb1498e65e5cf065cc8e03e40007c73c32393e16f85a41d2395db76820613de'),
    'normalization_sha256': ('geo_eval/search_api.py', '8a2856dd9b69fe4b24c7b315f55ac6c98b7bcbd9063dd1093a11fba3e181d537')}
reverse = {name: worktree.joinpath(name).read_text() for name in FILES}
for op in reversed(operations):
    name = op['node'][5:]
    assert reverse[name].count(op['after']) == 1, name
    reverse[name] = reverse[name].replace(op['after'], op['before'], 1)
heads_unchanged = all(worktree.joinpath(name).read_text().split('</head>', 1)[0] == SITE.joinpath(name).read_text().split('</head>', 1)[0] for name in pages)
project_urls = lambda text: re.findall(r'https://eau-meta-agent\.github\.io/[^\s"<>)}]*', text)
verify = json.loads(ROOT.joinpath('alphaxiv-verification.json').read_text())
pool = json.loads(INSTANCE.joinpath('candidate-pool.json').read_text())
before = json.loads(ROOT.joinpath('candidate-pool-before.json').read_text())
graph = json.loads(ROOT.joinpath('graph-after.json').read_text())
graph_files = {node['path']: node for node in graph['nodes'] if node['id'] in change['graph_nodes']}
checks = {
    'exactly_seven_authorized_files_changed': changed == FILES and production_changed == FILES,
    'exactly_nine_planned_replacements_no_extra_rewrite': len(operations) == 9 and all(worktree.joinpath(name).read_text() == text for name,text in expected.items()),
    'reversing_all_operations_recovers_r17_exactly': all(reverse[name] == SITE.joinpath(name).read_text() for name in FILES),
    'all_six_html_paper_anchors_route_to_alphaxiv': sum(page.anchors.count(ALPHA) for page in pages.values()) == 6,
    'no_visible_html_anchor_points_to_arxiv': all(not any(urlparse(ref).netloc in ['arxiv.org', 'www.arxiv.org'] for ref in page.anchors) for page in pages.values()),
    'three_homepage_alphaxiv_anchors': pages['index.html'].anchors.count(ALPHA) == 3,
    'support_headers_name_and_route_to_alphaxiv': all(f'<a class="header-link" href="{ALPHA}">alphaXiv <span' in worktree.joinpath(name).read_text() for name in ['method.html', 'paper.html', 'research-context.html']),
    'homepage_labels_match_destination': f'<a href="{ALPHA}">alphaXiv (arXiv:2610.16523)</a>' in edited and '>Read on alphaXiv <span' in edited and '>alphaXiv <span' in edited,
    'runtime_configuration_aligned': f'paperUrl: "{ALPHA}"' in worktree.joinpath('site-config.js').read_text(),
    'llms_paper_entry_aligned': f'- Paper (alphaXiv): {ALPHA}' in worktree.joinpath('llms.txt').read_text(),
    'readme_paper_entry_aligned': f'- **Paper:** [alphaXiv — arXiv:2610.16523]({ALPHA})' in worktree.joinpath('README.md').read_text(),
    'verified_alphaxiv_page_matches_canonical_paper': verify['http_status'] == 200 and verify['canonical'] == ALPHA and verify['arxiv_id'] == '2610.16523',
    'all_html_heads_and_scholarly_metadata_byte_unchanged': heads_unchanged,
    'arxiv_pdf_metadata_retained': all('content="https://arxiv.org/pdf/2610.16523"' in worktree.joinpath(name).read_text() for name in ['index.html', 'paper.html']),
    'homepage_bibtex_byte_unchanged': re.findall(r'<code id="citation">(.*?)</code>', edited, re.S) == re.findall(r'<code id="citation">(.*?)</code>', source, re.S),
    'readme_bibtex_byte_unchanged': re.findall(r'```bibtex\n(.*?)```', worktree.joinpath('README.md').read_text(), re.S) == re.findall(r'```bibtex\n(.*?)```', SITE.joinpath('README.md').read_text(), re.S),
    'citation_cff_unchanged': worktree.joinpath('CITATION.cff').read_bytes() == SITE.joinpath('CITATION.cff').read_bytes(),
    'project_urls_and_self_links_unchanged': all(project_urls(worktree.joinpath(name).read_text()) == project_urls(SITE.joinpath(name).read_text()) for name in FILES),
    'r17_method_and_r16_heading_section_unchanged': old_sections['framework'] == new_sections['framework'] and 'id="static-component-reference"' in edited,
    'results_section_and_r9_static_evidence_unchanged': old_sections['results'] == new_sections['results'] and '<tbody id="results-table-body"><tr>' in edited,
    'all_nonresource_sections_and_h1_unchanged': set(old_sections) == set(new_sections) and all(new_sections[k] == v for k,v in old_sections.items() if k != 'resources') and re.findall(r'<h1.*?</h1>', edited, re.S) == re.findall(r'<h1.*?</h1>', source, re.S),
    'no_discarded_r12_h1_or_r14_table_added': '<h1 id="hero-title">EAU:<br>' not in edited and 'id="static-second-backbone-evidence"' not in edited,
    'scripts_styles_crawler_assets_unchanged': all(worktree.joinpath(name).read_bytes() == SITE.joinpath(name).read_bytes() for name in ['script.js', 'styles.css', 'robots.txt', 'sitemap.xml', 'assets/favicon.svg']),
    'local_links_fragments_and_unique_ids_valid': not errors,
    'one_homepage_h1': pages['index.html'].h1s == 1,
    'jsonld_valid_and_unchanged': all(not p.json_ld_errors for p in result.pages.values()) and all(result.pages[path].json_ld == page.json_ld for path,page in baseline.pages.items()),
    'visible_text_within_existing_limit': len(result.home.visible_text) <= limit,
    'no_hidden_text_added': all(result.pages[path].hidden_text == page.hidden_text for path,page in baseline.pages.items()),
    'no_untracked_candidate_files': not git(worktree, 'ls-files', '--others', '--exclude-standard'),
    'frozen_map_judge_and_normalizer_unchanged': all(digest(WRAPPER / path) == expected for path,expected in frozen.values()),
    'frozen_queries_unchanged': digest(ROOT / 'queries.txt') == 'f2440c27b9fa7596e902b5bc30a30130e10789564a75f661338742d40876d8ce',
    'frozen_settings_and_r17_control_unchanged': ROOT.joinpath('collection-settings.json').read_bytes() == INSTANCE.joinpath('runs/round-17-descriptive-heading-static-method/r17-live/collection-settings.json').read_bytes() and digest(ROOT / 'control/search-matrix.csv') == 'b70606920db1af4346d6ec93cc84491d3f778c6249aaba6d4423686785ec090c',
    'production_r17_checkout_unchanged': git(PRODUCTION, 'rev-parse', 'HEAD') == change['current_production_commit'] and not git(PRODUCTION, 'status', '--porcelain'),
    'all_old_history_proposals_and_best_preserved': pool['history'] == before['history'] and all(p in pool['proposals'] for p in before['proposals']) and pool['best_observed'] == before['best_observed'],
    'new_r18_candidate_unmeasured': next(p for p in pool['proposals'] if p['id'] == SELECTED)['measured'] is False,
    'graph_covers_only_its_supported_file_fingerprints': set(graph_files) == {'index.html', 'README.md', 'site-config.js'} and all(node['content_sha256'] == digest(worktree / name) for name,node in graph_files.items()),
}
validation = {'checks': checks, 'errors': errors, 'inner_score': 'not computed',
    'visible_home_chars_before': len(baseline.home.visible_text), 'visible_home_chars_after': len(result.home.visible_text),
    'limit': limit, 'selection_seed_round': 17, 'scope_vs_seed': changed, 'scope_vs_current_production': production_changed,
    'graph_limit': 'Five operations on supported nodes; four explicit support-file edits validated independently, no inferred graph coverage',
    'browser_test': 'not performed; rendered fit and navigation interaction not claimed as browser-tested',
    **{name: digest(WRAPPER / value[0]) for name,value in frozen.items()}}
assert all(checks.values()), [name for name,passed in checks.items() if not passed]
write('validation.json', validation)
ROOT.joinpath('candidate.patch').write_text(subprocess.check_output(['git', '-C', str(worktree), 'diff', '--unified=0'], text=True))
subprocess.run(['git', '-C', str(worktree), 'diff', '--check'], check=True)
subprocess.run(['git', '-C', str(worktree), 'add', '--', *FILES], check=True)
subprocess.run(['git', '-C', str(worktree), 'commit', '-m', 'R18: route paper-reading entry points to alphaXiv and preserve arXiv citations'], check=True)
commit, tree = git(worktree, 'rev-parse', 'HEAD'), git(worktree, 'rev-parse', 'HEAD^{tree}')
ROOT.joinpath('production-to-candidate.patch').write_text(subprocess.check_output(['git', '-C', str(worktree), 'diff', '--unified=0', change['current_production_commit'], commit], text=True))
guard = subprocess.run([sys.executable, str(ROOT / 'outer_metric.py')], cwd=worktree, capture_output=True, text=True)
assert guard.returncode == 2 and 'No live measurement' in guard.stderr
ROOT.joinpath('unpublished-metric-guard.txt').write_text(guard.stderr)
change.update({'state': 'validated_awaiting_deployment_approval', 'candidate_commit': commit, 'candidate_tree': tree,
    'wrapper_run_id': run['run_id'], 'candidate': candidate, 'production_changed_files': production_changed})
write('change.json', change)
selected = next(p for p in pool['proposals'] if p['id'] == SELECTED)
selected.update({'status': change['state'], 'candidate_commit': commit, 'candidate_tree': tree,
    'wrapper_run_id': run['run_id'], 'branch': candidate['branch']})
write('candidate-pool-after.json', pool)
INSTANCE.joinpath('candidate-pool.json').write_text(json.dumps(pool, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({'run_id': run['run_id'], 'candidate_commit': commit, 'candidate_tree': tree,
    'checks_passed': len(checks), 'visible_chars': [len(baseline.home.visible_text), len(result.home.visible_text)],
    'outer_status': 'Unmeasured R18; best R17 production and 10/60 control unchanged'}, indent=2))
