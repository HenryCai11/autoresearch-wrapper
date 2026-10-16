"""Expose the existing second-backbone rows through one results-section insertion."""
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
assert not ROOT.joinpath('wrapper-candidate.json').exists(), 'Never allocate twice on a retry'
cli('evaluate', '--run-id', run['run_id'], '--candidate', 'seed', '--json', name='seed-evaluation.json')
seed = json.loads(cli('record', '--run-id', run['run_id'], '--candidate', 'seed', '--status', 'auto',
    '--description', 'Best preserved R9 control: 8/60; complete historical outer observation, not new R14 searches',
    '--json', name='seed-record.json'))
assert abs(seed['metric_value'] - 100 * 8 / 60) < 1e-9
candidate = json.loads(cli('allocate', '--run-id', run['run_id'], '--json', name='wrapper-candidate.json'))
worktree = Path(candidate['worktree_path'])
source = SITE.joinpath('index.html').read_text()
javascript = SITE.joinpath('script.js').read_text()

def backbone(key):
    match = re.search(r"  " + key + r": \{\s*label: '([^']+)',\s*rows: \[(.*?)\n    \],\s*\},", javascript, re.S)
    assert match, key
    raw_rows = re.findall(r"\['([^']+)',\s*([0-9.]+),\s*([0-9.]+),\s*([0-9.]+),\s*([0-9.]+)\]", match[2])
    assert len(raw_rows) == 9
    rows = [[row[0], *[format(Decimal(value), '.3f') for value in row[1:]]] for row in raw_rows]
    assert all(Decimal(0) <= Decimal(value) <= Decimal(1) for row in rows for value in row[1:])
    return {'label': match[1], 'rows': rows}

second, default = backbone('qwen25'), backbone('qwen3')
assert second['label'] == 'Qwen2.5-7B-Instruct' and default['label'] == 'Qwen3-4B'
head_match = re.search(r'<thead>.*?</thead>', source, re.S)
assert head_match
table_head = head_match[0]
row_html = []
for name, *values in second['rows']:
    ours = ' class="ours"' if name == 'eau' else ''
    row_html.append('          <tr' + ours + '><th scope="row">' + html.escape(name) + '</th>' +
                    ''.join('<td>' + value + '</td>' for value in values) + '</tr>')
addition = (
    '        <details class="result-table-details" id="static-second-backbone-evidence" open>\n'
    '          <summary>Qwen2.5-7B-Instruct: static result reference</summary>\n'
    '          <p class="results-note">The model switch above controls the main charts and comparison table. This separate reference always shows Qwen2.5-7B-Instruct.</p>\n'
    '          <div class="table-scroll"><table id="second-backbone-table"><caption id="second-backbone-caption">Qwen2.5-7B-Instruct · UserGym and ColBench (static reference)</caption>' +
    table_head + '<tbody id="second-backbone-table-body">\n' + '\n'.join(row_html) +
    '\n          </tbody></table></div>\n'
    '        </details>\n')
marker = '        <div class="tau-result">'
assert source.count(marker) == 1 and 'id="static-second-backbone-evidence"' not in source
write('static-second-backbone-source.json', {'source_file': 'script.js', 'source_sha256': digest(SITE / 'script.js'),
    'source_object': 'results.qwen25', 'label': second['label'], 'rows': second['rows'],
    'row_count': 9, 'numeric_value_count': 36, 'headers_html': table_head, 'rendered_html': addition,
    'facts': 'Existing JS result rows reproduced at the same three-decimal precision, without new claims, relative gains or tau2 numbers',
    'presentation': 'A default-open semantic details/table reference, independently captioned; not written by the existing model-switch renderer'})
write('operations.json', {'operations': [{'op': 'replace_text', 'node': 'file:index.html',
    'before': marker, 'after': addition + marker}]})
config, evidence = str(ROOT / 'config.json'), str(ROOT / 'r13-search-evidence.json')
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

class TableRows(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.rows, self.row, self.cell = [], None, None
        self.feed(text)
    def handle_starttag(self, tag, attrs):
        if tag == 'tr':
            self.row = []
        elif tag in ['td', 'th']:
            self.cell = ''
    def handle_data(self, data):
        if self.cell is not None:
            self.cell += data
    def handle_endtag(self, tag):
        if tag in ['td', 'th']:
            assert self.row is not None and self.cell is not None
            self.row.append(self.cell.strip())
            self.cell = None
        elif tag == 'tr':
            assert self.row is not None
            self.rows.append(self.row)
            self.row = None

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
new_tbody = re.search(r'<tbody id="second-backbone-table-body">(.*?)</tbody>', edited, re.S)[1]
old_tbody = re.search(r'<tbody id="results-table-body">(.*?)</tbody>', edited, re.S)[1]
frozen = {'knowledge_map_sha256': ('geo/instances/eau/map.json', '32be06bcafec6c3da9cf8360d86fa8e7154d6d05e1c46e598efd328c2d57973f'),
    'judge_sha256': ('geo_eval/discovery.py', '6bb1498e65e5cf065cc8e03e40007c73c32393e16f85a41d2395db76820613de'),
    'normalization_sha256': ('geo_eval/search_api.py', '8a2856dd9b69fe4b24c7b315f55ac6c98b7bcbd9063dd1093a11fba3e181d537')}
checks = {
    'only_index_changed_vs_best_seed': changed == ['index.html'],
    'exactly_one_insertion_preserving_every_original_byte': edited == source.replace(marker, addition + marker, 1),
    'only_results_named_section_changed': set(old_sections) == set(new_sections) and all(new_sections[k] == v for k,v in old_sections.items() if k != 'results') and old_sections['results'] != new_sections['results'],
    'all_nine_methods_and_36_values_match_existing_qwen25_js': TableRows(new_tbody).rows == second['rows'],
    'default_qwen3_rows_match_existing_js_and_are_not_replaced': TableRows(old_tbody).rows == default['rows'],
    'new_model_label_and_independent_caption_are_explicit': second['label'] + ' · UserGym and ColBench (static reference)' in edited and edited.count('id="second-backbone-caption"') == 1,
    'new_reference_open_by_default_not_script_gated': 'id="static-second-backbone-evidence" open>' in addition and '<noscript' not in addition and '<script' not in addition and 'hidden' not in addition and 'display:' not in addition,
    'no_new_backbone_gains_or_tau2_numbers': 'tau' not in addition.lower() and 'τ' not in addition and '%' not in addition,
    'same_existing_column_headers_and_table_styles': table_head in addition and 'class="result-table-details"' in addition and 'class="table-scroll"' in addition,
    'new_static_ids_not_targets_of_switch_renderer': all('#' + name not in javascript for name in ['second-backbone-table', 'second-backbone-table-body', 'second-backbone-caption', 'static-second-backbone-evidence']),
    'main_charts_and_original_table_ids_preserved_once': all(edited.count('id="' + name + '"') == 1 for name in ['result-charts', 'table-caption', 'results-table-body']),
    'model_switch_default_and_both_buttons_unchanged': '<button data-model="qwen3" aria-pressed="true">Qwen3-4B</button><button data-model="qwen25" aria-pressed="false">Qwen2.5-7B</button>' in edited and "renderResults('qwen3');" in javascript,
    'no_r13_static_component_block_inherited': 'id="static-component-reference"' not in edited,
    'h1_unchanged_from_selection_seed': re.findall(r'<h1.*?</h1>', edited, re.S) == re.findall(r'<h1.*?</h1>', source, re.S),
    'head_metadata_and_schema_bytes_unchanged': edited.split('</head>', 1)[0] == source.split('</head>', 1)[0],
    'script_and_style_bytes_unchanged': all(worktree.joinpath(name).read_bytes() == SITE.joinpath(name).read_bytes() for name in ['script.js', 'styles.css', 'site-config.js']),
    'no_untracked_candidate_files': not git(worktree, 'ls-files', '--others', '--exclude-standard'),
    'local_links_fragments_and_unique_ids_valid': not errors,
    'one_homepage_h1': pages['index.html'].h1s == 1,
    'jsonld_valid_and_unchanged': all(not p.json_ld_errors for p in result.pages.values()) and all(result.pages[path].json_ld == page.json_ld for path,page in baseline.pages.items()),
    'visible_text_within_existing_limit': len(result.home.visible_text) <= limit,
    'no_hidden_text_added': result.home.hidden_text == baseline.home.hidden_text,
    'all_nonhome_visible_content_unchanged': all(result.pages[path].visible_text == page.visible_text for path,page in baseline.pages.items() if path != '/'),
    'frozen_map_judge_and_normalizer_unchanged': all(digest(WRAPPER / path) == expected for path,expected in frozen.values()),
    'query_set_unchanged': digest(ROOT / 'queries.txt') == 'f2440c27b9fa7596e902b5bc30a30130e10789564a75f661338742d40876d8ce',
    'production_r13_checkout_unchanged': git(PRODUCTION, 'rev-parse', 'HEAD') == change['current_production_commit'] and not git(PRODUCTION, 'status', '--porcelain'),
    'production_diff_has_only_index': production_changed == ['index.html'],
}
validation = {'checks': checks, 'errors': errors, 'inner_score': 'not computed',
    'visible_home_chars_before': len(baseline.home.visible_text), 'visible_home_chars_after': len(result.home.visible_text),
    'limit': limit, 'selection_seed_round': 9, 'source_rows': 9, 'source_numeric_values': 36,
    'scope_vs_seed': changed, 'scope_vs_current_production': production_changed,
    'browser_test': 'not performed; existing styles/selectors remain but rendered layout and interactive behavior are not claimed as browser-tested',
    **{name: digest(WRAPPER / value[0]) for name,value in frozen.items()}}
write('validation.json', validation)
assert all(checks.values()), [name for name,passed in checks.items() if not passed]
ROOT.joinpath('candidate.patch').write_text(subprocess.check_output(['git', '-C', str(worktree), 'diff', '--unified=0'], text=True))
subprocess.run(['git', '-C', str(worktree), 'diff', '--check'], check=True)
subprocess.run(['git', '-C', str(worktree), 'add', '--', 'index.html'], check=True)
subprocess.run(['git', '-C', str(worktree), 'commit', '-m', 'R14: expose existing Qwen2.5 result rows in a static reference table'], check=True)
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
assert pool['current_round'] == 14 and pool['selected_candidate_id'] == SELECTED
selected = next(p for p in pool['proposals'] if p['id'] == SELECTED)
selected.update({'status': change['state'], 'candidate_commit': commit, 'candidate_tree': tree,
    'wrapper_run_id': run['run_id'], 'branch': candidate['branch']})
write('candidate-pool-after.json', pool)
pool_path.write_text(json.dumps(pool, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({'run_id': run['run_id'], 'candidate_commit': commit, 'candidate_tree': tree,
    'checks_passed': len(checks), 'visible_chars': [len(baseline.home.visible_text), len(result.home.visible_text)],
    'source_rows': 9, 'source_numeric_values': 36, 'outer_status': 'Unmeasured; current R13 production unchanged'}, indent=2))
