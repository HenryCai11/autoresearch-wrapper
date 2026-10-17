"""Apply two factual H2 labels in an allocated R16 worktree; no live scoring yet."""
import html
import re
import sys
from collections import Counter
from decimal import Decimal
from html.parser import HTMLParser
from urllib.parse import unquote, urlparse
from common import *
from autoresearch_wrapper.geo import SectionParser
from geo_eval.site import load_site

assert os.environ.get('SLURM_JOB_ID')
run = json.loads(ROOT.joinpath('wrapper-run.json').read_text())
change = json.loads(ROOT.joinpath('change.json').read_text())
assert not ROOT.joinpath('wrapper-candidate.json').exists(), 'Do not allocate twice'
cli('evaluate', '--run-id', run['run_id'], '--candidate', 'seed', '--json', name='seed-evaluation.json')
seed = json.loads(cli('record', '--run-id', run['run_id'], '--candidate', 'seed', '--status', 'auto',
    '--description', 'Preserved best R9 8/60 historical outer control; not new R16 searches',
    '--json', name='seed-record.json'))
assert abs(seed['metric_value'] - 100 * 8 / 60) < 1e-9
candidate = json.loads(cli('allocate', '--run-id', run['run_id'], '--json', name='wrapper-candidate.json'))
worktree = Path(candidate['worktree_path'])
source = SITE.joinpath('index.html').read_text()
javascript = SITE.joinpath('script.js').read_text()
manifest = json.loads(ROOT.joinpath('heading-source.json').read_text())
operations = json.loads(ROOT.joinpath('operations.json').read_text())['operations']
assert len(operations) == manifest['operation_count'] == 2
expected = source
for operation in operations:
    assert operation['op'] == 'replace_text' and operation['node'] == 'file:index.html'
    assert expected.count(operation['before']) == 1
    expected = expected.replace(operation['before'], operation['after'], 1)
config, evidence = str(ROOT / 'config.json'), str(ROOT / 'r15-search-evidence.json')
for command, output in [('geo-graph', 'graph-before.json'), ('geo-prioritize', 'priorities.json'),
                        ('geo-decide', 'decision.json'), ('geo-explore', 'exploration.json')]:
    args = [command, '--config', config]
    if command != 'geo-graph':
        args += ['--search-evidence', evidence]
    cli(*args, name=output, repo=worktree)
cli('geo-apply', '--config', config, '--operations', str(ROOT / 'operations.json'), name='preview.json', repo=worktree)
cli('geo-apply', '--config', config, '--operations', str(ROOT / 'operations.json'), '--apply', name='applied.json', repo=worktree)
cli('geo-graph', '--config', config, name='graph-after.json', repo=worktree)

def sections(text):
    parser = SectionParser(text)
    parser.feed(text)
    return {key: text[span[0]:span[1]] for key,span in parser.sections.items()}

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
for name,page in pages.items():
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
facts = {node['id']: node for node in json.loads(INSTANCE.joinpath('map.json').read_text())['nodes']}
heading_facts_valid = all(item['fact'] == facts[item['map_node']]['fact'] and
    item['existing_source_excerpt'] in SITE.joinpath(item['existing_visible_source'].split('#')[0]).read_text()
    for item in manifest['headings'])
restored = edited
for operation in reversed(operations):
    assert restored.count(operation['after']) == 1
    restored = restored.replace(operation['after'], operation['before'], 1)
visible = ' '.join(result.home.visible_text.split())
def fragment(text, tag, element_id):
    return re.search(r'<' + tag + r'\b[^>]*\bid="' + re.escape(element_id) + r'"[^>]*>.*?</' + tag + '>', text, re.S)[0]
frozen = {'knowledge_map_sha256': ('geo/instances/eau/map.json', '32be06bcafec6c3da9cf8360d86fa8e7154d6d05e1c46e598efd328c2d57973f'),
    'judge_sha256': ('geo_eval/discovery.py', '6bb1498e65e5cf065cc8e03e40007c73c32393e16f85a41d2395db76820613de'),
    'normalization_sha256': ('geo_eval/search_api.py', '8a2856dd9b69fe4b24c7b315f55ac6c98b7bcbd9063dd1093a11fba3e181d537')}
checks = {
    'only_index_changed_vs_best_seed': changed == ['index.html'],
    'exactly_two_heading_operations_no_extra_rewrite': edited == expected and len(operations) == 2,
    'reverse_two_operations_recovers_entire_seed_html': restored == source,
    'only_framework_and_results_named_sections_changed': set(old_sections) == set(new_sections) and {key for key in old_sections if old_sections[key] != new_sections[key]} == {'framework', 'results'},
    'headings_supported_by_frozen_map_and_existing_visible_sources': heading_facts_valid and manifest['new_facts'] is False,
    'only_framework_h2_changed_within_its_section': new_sections['framework'] == old_sections['framework'].replace(operations[0]['before'], operations[0]['after'], 1),
    'only_results_h2_changed_within_its_section': new_sections['results'] == old_sections['results'].replace(operations[1]['before'], operations[1]['after'], 1),
    'new_headings_present_in_visible_text': 'How EAU adapts the training system.' in visible and 'EAU results on UserGym and ColBench.' in visible,
    'h2_count_ids_and_order_preserved': re.findall(r'<h2\b[^>]*>', source) == re.findall(r'<h2\b[^>]*>', edited),
    'h2_br_and_em_structure_preserved': all(op['after'].count('<br>') == op['before'].count('<br>') == 1 and op['after'].count('<em>') == op['before'].count('<em>') == 1 for op in operations),
    'section_accessible_heading_targets_preserved': all('aria-labelledby="' + name + '"' in edited for name in ['framework-title', 'results-title']),
    'original_r9_h1_and_subtitle_unchanged': fragment(edited, 'h1', 'hero-title') == fragment(source, 'h1', 'hero-title') and '<p class="hero-subtitle">Environment–Agent–User Co-evolution<br>for Training User-Centric Agents</p>' in edited,
    'r7_overview_unchanged': old_sections['overview'] == new_sections['overview'],
    'r9_default_static_result_table_byte_identical': fragment(edited, 'tbody', 'results-table-body') == fragment(source, 'tbody', 'results-table-body'),
    'discarded_r15_static_blocks_not_inherited': all(name not in edited for name in ['id="static-component-reference"', 'id="static-second-backbone-evidence"']),
    'old_interactive_targets_preserved_once': all(edited.count('id="' + name + '"') == 1 for name in ['component-panel', 'component-title', 'component-description', 'component-knobs', 'result-charts', 'results-table-body', 'table-caption']),
    'default_model_selection_and_renderer_preserved': '<button data-model="qwen3" aria-pressed="true">Qwen3-4B</button><button data-model="qwen25" aria-pressed="false">Qwen2.5-7B</button>' in edited and "renderResults('qwen3');" in javascript,
    'head_metadata_and_schema_bytes_unchanged': edited.split('</head>', 1)[0] == source.split('</head>', 1)[0],
    'scripts_and_styles_byte_identical_to_seed': all(worktree.joinpath(name).read_bytes() == SITE.joinpath(name).read_bytes() for name in ['script.js', 'styles.css', 'site-config.js']),
    'all_reference_urls_and_order_unchanged': all(page.refs == Elements(SITE.joinpath(name).read_text()).refs for name,page in pages.items()),
    'no_untracked_candidate_files': not git(worktree, 'ls-files', '--others', '--exclude-standard'),
    'local_links_fragments_and_unique_ids_valid': not errors,
    'one_homepage_h1': pages['index.html'].h1s == 1,
    'jsonld_valid_and_unchanged': all(not p.json_ld_errors for p in result.pages.values()) and all(result.pages[path].json_ld == page.json_ld for path,page in baseline.pages.items()),
    'visible_text_within_original_limit': len(result.home.visible_text) <= limit,
    'no_hidden_text_added': result.home.hidden_text == baseline.home.hidden_text,
    'all_nonhome_visible_content_unchanged': all(result.pages[path].visible_text == page.visible_text for path,page in baseline.pages.items() if path != '/'),
    'frozen_map_judge_and_normalizer_unchanged': all(digest(WRAPPER / path) == expected_hash for path,expected_hash in frozen.values()),
    'frozen_queries_unchanged': digest(ROOT / 'queries.txt') == 'f2440c27b9fa7596e902b5bc30a30130e10789564a75f661338742d40876d8ce',
    'production_r15_checkout_unchanged': git(PRODUCTION, 'rev-parse', 'HEAD') == change['current_production_commit'] and not git(PRODUCTION, 'status', '--porcelain'),
    'production_diff_only_index': production_changed == ['index.html'],
}
validation = {'checks': checks, 'errors': errors, 'inner_score': 'not computed',
    'visible_home_chars_before': len(baseline.home.visible_text), 'visible_home_chars_after': len(result.home.visible_text),
    'limit': limit, 'selection_seed_round': 9, 'heading_operation_count': 2,
    'scope_vs_seed': changed, 'scope_vs_current_production': production_changed,
    'browser_test': 'not performed; preserved br/em structure and existing styles do not establish rendered line wrapping, layout or runtime behavior',
    **{name: digest(WRAPPER / value[0]) for name,value in frozen.items()}}
write('validation.json', validation)
write('heading-source-checks.json', {'headings': manifest['headings'], 'source_facts_verified': heading_facts_valid,
    'default_static_tbody_sha256': hashlib.sha256(fragment(edited, 'tbody', 'results-table-body').encode()).hexdigest(),
    'script_sha256': digest(SITE / 'script.js'), 'facts': 'Only factual headings changed; all data and paragraphs unchanged; outer score unknown'})
assert all(checks.values()), [name for name,passed in checks.items() if not passed]
ROOT.joinpath('candidate.patch').write_text(subprocess.check_output(['git', '-C', str(worktree), 'diff', '--unified=0'], text=True))
subprocess.run(['git', '-C', str(worktree), 'diff', '--check'], check=True)
subprocess.run(['git', '-C', str(worktree), 'add', '--', 'index.html'], check=True)
subprocess.run(['git', '-C', str(worktree), 'commit', '-m', 'R16: make framework and benchmark section headings descriptive'], check=True)
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
assert pool['current_round'] == 16 and pool['selected_candidate_id'] == SELECTED
selected = next(p for p in pool['proposals'] if p['id'] == SELECTED)
selected.update({'status': change['state'], 'candidate_commit': commit, 'candidate_tree': tree,
    'wrapper_run_id': run['run_id'], 'branch': candidate['branch']})
write('candidate-pool-after.json', pool)
pool_path.write_text(json.dumps(pool, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({'run_id': run['run_id'], 'candidate_commit': commit, 'candidate_tree': tree,
    'checks_passed': len(checks), 'visible_chars': [len(baseline.home.visible_text), len(result.home.visible_text)],
    'outer_status': 'Unmeasured heading candidate; R15 production unchanged'}, indent=2))
