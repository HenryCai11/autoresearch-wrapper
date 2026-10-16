"""Apply one static framework-reference intervention in the allocated worktree."""
import html
import re
import sys
from collections import Counter
from html.parser import HTMLParser
from urllib.parse import unquote, urlparse
from common import *
from autoresearch_wrapper.geo import SectionParser
from geo_eval.site import load_site

assert os.environ.get('SLURM_JOB_ID')
run = json.loads(ROOT.joinpath('wrapper-run.json').read_text())
change = json.loads(ROOT.joinpath('change.json').read_text())
context = json.loads(ROOT.joinpath('production-context.json').read_text())
assert not ROOT.joinpath('validation.json').exists(), 'A validated candidate must not be rerun'
if not ROOT.joinpath('wrapper-candidate.json').exists():
    cli('evaluate', '--run-id', run['run_id'], '--candidate', 'seed', '--json', name='seed-evaluation.json')
    seed = json.loads(cli('record', '--run-id', run['run_id'], '--candidate', 'seed', '--status', 'auto',
        '--description', f"Preserved best R{context['selection_seed_round']} control: {context['seed_observation']['project_citations']}/60; historical observation, not new collection",
        '--json', name='seed-record.json'))
    candidate = json.loads(cli('allocate', '--run-id', run['run_id'], '--json', name='wrapper-candidate.json'))
else:
    seed = json.loads(ROOT.joinpath('seed-record.json').read_text())
    candidate = json.loads(ROOT.joinpath('wrapper-candidate.json').read_text())
    assert change['state'] == 'preparing'
    assert git(Path(candidate['worktree_path']), 'rev-parse', 'HEAD') == change['selection_seed_commit']
assert abs(seed['metric_value'] - 100 * context['seed_observation']['project_citations'] / 60) < 1e-9
worktree = Path(candidate['worktree_path'])
source = SITE.joinpath('index.html').read_text()
javascript = SITE.joinpath('script.js').read_text()
components = {}
for name in ['environment', 'agent']:
    match = re.search(r"  " + name + r": \{\n    title: '([^']*)',\n    description: '([^']*)',\n    knobs: \[([^\n]*)\],\n  \},", javascript)
    assert match, name
    components[name] = {'title': match[1], 'description': match[2], 'knobs': re.findall(r"'([^']*)'", match[3])}
    assert len(components[name]['knobs']) == 3
articles = []
for name, data in components.items():
    articles.append('        <article><span class="mini-index">Evolving ' + name + '</span><h3>' +
        html.escape(data['title']) + '</h3><p>' + html.escape(data['description']) +
        '</p><div class="knob-list">' + ''.join('<span>' + html.escape(k) + '</span>' for k in data['knobs']) +
        '</div></article>')
addition = '      <div class="timescales" id="static-component-reference" aria-label="Environment and agent reference">\n' + '\n'.join(articles) + '\n      </div>\n'
marker = '      <div class="timescales"><article><span class="mini-index">Within a run'
assert source.count(marker) == 1 and 'id="static-component-reference"' not in source
write('static-component-source.json', {'source_file': 'script.js', 'source_sha256': digest(SITE / 'script.js'),
    'components': components, 'rendered_html': addition,
    'facts': 'Titles, descriptions and knob labels copied verbatim from existing public JS data; no new method claim or measurement',
    'presentation': 'Persistent semantic article blocks using existing styles; unchanged interactive tabs remain above, no duplicated default user paragraph'})
write('operations.json', {'operations': [{'op': 'replace_text', 'node': 'file:index.html',
    'before': marker, 'after': addition + marker}]})
config, evidence = str(ROOT / 'config.json'), str(ROOT / 'r12-search-evidence.json')
if not ROOT.joinpath('applied.json').exists():
    for command, output in [('geo-graph', 'graph-before.json'), ('geo-prioritize', 'priorities.json'),
                            ('geo-decide', 'decision.json'), ('geo-explore', 'exploration.json')]:
        args = [command, '--config', config]
        if command != 'geo-graph':
            args += ['--search-evidence', evidence]
        cli(*args, name=output, repo=worktree)
    cli('geo-apply', '--config', config, '--operations', str(ROOT / 'operations.json'), name='preview.json', repo=worktree)
    cli('geo-apply', '--config', config, '--operations', str(ROOT / 'operations.json'), '--apply', name='applied.json', repo=worktree)
    cli('geo-graph', '--config', config, name='graph-after.json', repo=worktree)
else:
    assert worktree.joinpath('index.html').read_text() == source.replace(marker, addition + marker, 1)
    assert ROOT.joinpath('graph-before.json').is_file() and ROOT.joinpath('graph-after.json').is_file()
    write('preparation-recovery.json', {'cause': 'The local clone did not contain the latest production merge object needed for the production diff; first validation stopped before writing a metric or candidate commit.',
        'resolution': 'Fetched origin/main on the login node, then resumed the same allocated candidate without a second seed record, allocation or edit.',
        'preserved': ['original geo-apply preview and application', 'graph-before and graph-after', 'original failed Slurm log prepare-1797109.out'],
        'no_search_or_deployment': True})

def sections(text):
    parser = SectionParser(text)
    parser.feed(text)
    return {key: text[span[0]:span[1]] for key, span in parser.sections.items()}

class Elements(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.ids, self.refs, self.h1s = [], [], 0
        self.feed(text)
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if 'id' in attrs:
            self.ids.append(attrs['id'])
        self.h1s += tag == 'h1'
        if tag in ['a', 'link', 'script', 'img']:
            ref = attrs.get('href') or attrs.get('src')
            if ref:
                self.refs.append(ref)

edited = worktree.joinpath('index.html').read_text()
old_sections, new_sections = sections(source), sections(edited)
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
baseline, result = load_site(str(SITE)), load_site(str(worktree))
changed = git(worktree, 'diff', '--name-only').splitlines()
production_changed = git(worktree, 'diff', change['current_production_commit'], '--name-only').splitlines()
limit = json.loads(INSTANCE.joinpath('map.json').read_text())['limits']['max_visible_chars']
frozen = {'knowledge_map_sha256': ('geo/instances/eau/map.json', '32be06bcafec6c3da9cf8360d86fa8e7154d6d05e1c46e598efd328c2d57973f'),
    'judge_sha256': ('geo_eval/discovery.py', '6bb1498e65e5cf065cc8e03e40007c73c32393e16f85a41d2395db76820613de'),
    'normalization_sha256': ('geo_eval/search_api.py', '8a2856dd9b69fe4b24c7b315f55ac6c98b7bcbd9063dd1093a11fba3e181d537')}
explorer = source.split('      <div class="framework-explorer">', 1)[1].split(marker, 1)[0]
checks = {
    'only_index_changed_vs_best_seed': changed == ['index.html'],
    'exactly_one_insertion_and_no_other_rewrite': edited == source.replace(marker, addition + marker, 1),
    'only_framework_named_section_changed': set(old_sections) == set(new_sections) and all(new_sections[k] == v for k,v in old_sections.items() if k != 'framework') and old_sections['framework'] != new_sections['framework'],
    'both_static_descriptions_match_existing_js_verbatim': all(html.escape(v['description']) in addition and html.escape(v['title']) in addition for v in components.values()),
    'all_six_knob_labels_match_existing_js': all(html.escape(knob) in addition for v in components.values() for knob in v['knobs']),
    'default_user_description_not_duplicated': 'Combine explicit symbolic rules' not in addition,
    'interactive_explorer_bytes_preserved': explorer in edited,
    'static_blocks_not_hidden_or_script_gated': '<script' not in addition and '<noscript' not in addition and '<details' not in addition and 'hidden' not in addition and 'display:' not in addition,
    'existing_two_column_and_knob_styles_reused': 'class="timescales"' in addition and addition.count('class="knob-list"') == 2,
    'h1_unchanged_from_selection_seed': re.findall(r'<h1.*?</h1>', edited, re.S) == re.findall(r'<h1.*?</h1>', source, re.S),
    'head_and_metadata_bytes_unchanged': edited.split('</head>', 1)[0] == source.split('</head>', 1)[0],
    'static_benchmark_results_unchanged': old_sections['results'] == new_sections['results'] and '<tbody id="results-table-body"><tr>' in edited,
    'no_untracked_candidate_files': not git(worktree, 'ls-files', '--others', '--exclude-standard'),
    'local_links_fragments_and_unique_ids_valid': not errors,
    'one_homepage_h1': pages['index.html'].h1s == 1,
    'jsonld_valid_and_unchanged': all(not p.json_ld_errors for p in result.pages.values()) and all(result.pages[path].json_ld == page.json_ld for path,page in baseline.pages.items()),
    'visible_text_within_existing_limit': len(result.home.visible_text) <= limit,
    'no_hidden_text_added': result.home.hidden_text == baseline.home.hidden_text,
    'all_nonhome_visible_content_unchanged': all(result.pages[path].visible_text == page.visible_text for path,page in baseline.pages.items() if path != '/'),
    'frozen_map_judge_and_normalizer_unchanged': all(digest(WRAPPER / path) == expected for path,expected in frozen.values()),
    'query_set_unchanged': digest(ROOT / 'queries.txt') == 'f2440c27b9fa7596e902b5bc30a30130e10789564a75f661338742d40876d8ce',
    'production_r12_checkout_unchanged': git(PRODUCTION, 'rev-parse', 'HEAD') == change['current_production_commit'] and not git(PRODUCTION, 'status', '--porcelain'),
    'production_diff_has_only_index': production_changed == ['index.html'],
}
validation = {'checks': checks, 'errors': errors, 'inner_score': 'not computed',
    'visible_home_chars_before': len(baseline.home.visible_text), 'visible_home_chars_after': len(result.home.visible_text),
    'limit': limit, 'selection_seed_round': context['selection_seed_round'],
    'scope_vs_seed': changed, 'scope_vs_current_production': production_changed,
    'browser_test': 'not performed; existing styles reused but rendered fit and interactive behavior not claimed as browser-tested',
    **{name: digest(WRAPPER / value[0]) for name,value in frozen.items()}}
write('validation.json', validation)
assert all(checks.values()), [name for name,passed in checks.items() if not passed]
ROOT.joinpath('candidate.patch').write_text(subprocess.check_output(['git', '-C', str(worktree), 'diff', '--unified=0'], text=True))
subprocess.run(['git', '-C', str(worktree), 'diff', '--check'], check=True)
subprocess.run(['git', '-C', str(worktree), 'add', '--', 'index.html'], check=True)
subprocess.run(['git', '-C', str(worktree), 'commit', '-m', 'R13: expose existing environment and agent descriptions as static HTML'], check=True)
commit, tree = git(worktree, 'rev-parse', 'HEAD'), git(worktree, 'rev-parse', 'HEAD^{tree}')
ROOT.joinpath('production-to-candidate.patch').write_text(subprocess.check_output(['git', '-C', str(worktree), 'diff', '--unified=0', change['current_production_commit'], commit], text=True))
guard = subprocess.run([sys.executable, str(ROOT / 'outer_metric.py')], cwd=worktree, capture_output=True, text=True)
assert guard.returncode == 2 and 'No live measurement' in guard.stderr
ROOT.joinpath('unpublished-metric-guard.txt').write_text(guard.stderr)
change.update({'state': 'validated_awaiting_deployment_approval', 'candidate_commit': commit, 'candidate_tree': tree,
    'wrapper_run_id': run['run_id'], 'candidate': candidate, 'production_changed_files': production_changed})
write('change.json', change)
pool_path = INSTANCE / 'candidate-pool.json'
pool = json.loads(pool_path.read_text())
assert pool['current_round'] == 13 and pool['selected_candidate_id'] == SELECTED
selected = next(p for p in pool['proposals'] if p['id'] == SELECTED)
selected.update({'status': change['state'], 'candidate_commit': commit, 'candidate_tree': tree,
    'wrapper_run_id': run['run_id'], 'branch': candidate['branch']})
write('candidate-pool-after.json', pool)
pool_path.write_text(json.dumps(pool, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({'run_id': run['run_id'], 'candidate_commit': commit, 'candidate_tree': tree,
    'checks_passed': len(checks), 'visible_chars': [len(baseline.home.visible_text), len(result.home.visible_text)],
    'outer_status': 'Unmeasured; current production R12 unchanged'}, indent=2))
