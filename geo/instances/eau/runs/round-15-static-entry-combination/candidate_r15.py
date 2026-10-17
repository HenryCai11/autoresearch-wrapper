"""Replay the three retained parent operations in one allocated combination worktree."""
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
    '--description', 'Preserved best R9 8/60 historical outer control; not new R15 searches',
    '--json', name='seed-record.json'))
assert abs(seed['metric_value'] - 100 * 8 / 60) < 1e-9
candidate = json.loads(cli('allocate', '--run-id', run['run_id'], '--json', name='wrapper-candidate.json'))
worktree = Path(candidate['worktree_path'])
source = SITE.joinpath('index.html').read_text()
javascript = SITE.joinpath('script.js').read_text()
manifest = json.loads(ROOT.joinpath('combination-source.json').read_text())
operations = json.loads(ROOT.joinpath('operations.json').read_text())['operations']
assert len(operations) == 3
expected = source
for parent, operation in zip(manifest['parents'], operations):
    assert digest(ROOT / parent['operations']) == parent['operations_sha256']
    assert json.loads(ROOT.joinpath(parent['operations']).read_text())['operations'] == [operation]
    assert expected.count(operation['before']) == 1
    expected = expected.replace(operation['before'], operation['after'], 1)
config, evidence = str(ROOT / 'config.json'), str(ROOT / 'r14-search-evidence.json')
for command, output in [('geo-graph', 'graph-before.json'), ('geo-prioritize', 'priorities.json'),
                        ('geo-decide', 'decision.json'), ('geo-explore', 'exploration.json')]:
    args = [command, '--config', config]
    if command != 'geo-graph':
        args += ['--search-evidence', evidence]
    cli(*args, name=output, repo=worktree)
cli('geo-apply', '--config', config, '--operations', str(ROOT / 'operations.json'), name='preview.json', repo=worktree)
cli('geo-apply', '--config', config, '--operations', str(ROOT / 'operations.json'), '--apply', name='applied.json', repo=worktree)
cli('geo-graph', '--config', config, name='graph-after.json', repo=worktree)

def backbone(key):
    match = re.search(r"  " + key + r": \{\s*label: '([^']+)',\s*rows: \[(.*?)\n    \],\s*\},", javascript, re.S)
    assert match, key
    raw_rows = re.findall(r"\['([^']+)',\s*([0-9.]+),\s*([0-9.]+),\s*([0-9.]+),\s*([0-9.]+)\]", match[2])
    assert len(raw_rows) == 9
    rows = [[row[0], *[format(Decimal(value), '.3f') for value in row[1:]]] for row in raw_rows]
    assert all(Decimal(0) <= Decimal(value) <= Decimal(1) for row in rows for value in row[1:])
    return {'label': match[1], 'rows': rows}


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
second, default = backbone('qwen25'), backbone('qwen3')
new_tbody = re.search(r'<tbody id="second-backbone-table-body">(.*?)</tbody>', edited, re.S)[1]
default_tbody = re.search(r'<tbody id="results-table-body">(.*?)</tbody>', edited, re.S)[1]
components = {}
for name in ['environment', 'agent']:
    match = re.search(r"  " + name + r": \{\n    title: '([^']*)',\n    description: '([^']*)',\n    knobs: \[([^\n]*)\],\n  \},", javascript)
    assert match
    components[name] = {'title': match[1], 'description': match[2], 'knobs': re.findall(r"'([^']*)'", match[3])}
method_addition = operations[1]['after'][:-len(operations[1]['before'])]
table_addition = operations[2]['after'][:-len(operations[2]['before'])]
parent13 = subprocess.check_output(['git', '-C', str(SITE), 'show', manifest['parents'][1]['candidate_commit'] + ':index.html'], text=True)
parent14 = PRODUCTION.joinpath('index.html').read_text()
history = {entry['id']: entry for entry in json.loads(ROOT.joinpath('candidate-pool-before.json').read_text())['history']}
frozen = {'knowledge_map_sha256': ('geo/instances/eau/map.json', '32be06bcafec6c3da9cf8360d86fa8e7154d6d05e1c46e598efd328c2d57973f'),
    'judge_sha256': ('geo_eval/discovery.py', '6bb1498e65e5cf065cc8e03e40007c73c32393e16f85a41d2395db76820613de'),
    'normalization_sha256': ('geo_eval/search_api.py', '8a2856dd9b69fe4b24c7b315f55ac6c98b7bcbd9063dd1093a11fba3e181d537')}
checks = {
    'only_index_changed_vs_best_seed': changed == ['index.html'],
    'exactly_three_archived_operations_no_extra_rewrite': edited == expected,
    'parent_operations_unchanged_in_original_archives': all(digest(INSTANCE / history[f"r{p['round']}"]['artifact_dir'] / 'operations.json') == p['operations_sha256'] for p in manifest['parents']),
    'only_framework_and_results_named_sections_changed': set(old_sections) == set(new_sections) and {key for key in old_sections if old_sections[key] != new_sections[key]} == {'framework', 'results'},
    'h1_exactly_reuses_r12_operation': edited.count(operations[0]['after']) == 1 and operations[0]['before'] not in edited,
    'full_paper_title_stays_in_original_subtitle': '<p class="hero-subtitle">Environment–Agent–User Co-evolution<br>for Training User-Centric Agents</p>' in edited,
    'h1_id_two_line_br_em_structure_preserved': 'aria-labelledby="hero-title"' in edited and operations[0]['after'].count('<br>') == operations[0]['before'].count('<br>') == 1 and '<em>' in operations[0]['after'],
    'framework_bytes_equal_retained_r13_parent': new_sections['framework'] == sections(parent13)['framework'],
    'results_bytes_equal_current_r14_parent': new_sections['results'] == sections(parent14)['results'],
    'environment_and_agent_text_matches_existing_js': all(html.escape(v['title']) in method_addition and html.escape(v['description']) in method_addition for v in components.values()),
    'all_six_component_knob_labels_match_existing_js': sum(len(v['knobs']) for v in components.values()) == 6 and all(html.escape(knob) in method_addition for v in components.values() for knob in v['knobs']),
    'default_user_description_not_duplicated': 'Combine explicit symbolic rules' not in method_addition,
    'all_nine_second_backbone_rows_and_36_values_match_js': TableRows(new_tbody).rows == second['rows'] and len(second['rows']) == 9,
    'all_default_backbone_rows_still_match_js': TableRows(default_tbody).rows == default['rows'],
    'second_backbone_explicit_caption_and_default_open': second['label'] + ' · UserGym and ColBench (static reference)' in edited and 'id="static-second-backbone-evidence" open>' in edited,
    'no_new_gains_or_tau2_results_in_reused_table': 'tau' not in table_addition.lower() and 'τ' not in table_addition and '%' not in table_addition,
    'old_interactive_targets_preserved_once': all(edited.count('id="' + name + '"') == 1 for name in ['component-panel', 'component-title', 'component-description', 'component-knobs', 'result-charts', 'results-table-body', 'table-caption']),
    'default_model_selection_and_renderer_preserved': '<button data-model="qwen3" aria-pressed="true">Qwen3-4B</button><button data-model="qwen25" aria-pressed="false">Qwen2.5-7B</button>' in edited and "renderResults('qwen3');" in javascript,
    'static_reference_ids_are_not_switch_renderer_targets': all('#' + name not in javascript for name in ['static-component-reference', 'second-backbone-table', 'second-backbone-table-body', 'second-backbone-caption']),
    'head_metadata_and_schema_bytes_unchanged': edited.split('</head>', 1)[0] == source.split('</head>', 1)[0],
    'scripts_and_styles_byte_identical_to_seed': all(worktree.joinpath(name).read_bytes() == SITE.joinpath(name).read_bytes() for name in ['script.js', 'styles.css', 'site-config.js']),
    'no_untracked_candidate_files': not git(worktree, 'ls-files', '--others', '--exclude-standard'),
    'local_links_fragments_and_unique_ids_valid': not errors,
    'one_homepage_h1': pages['index.html'].h1s == 1,
    'jsonld_valid_and_unchanged': all(not p.json_ld_errors for p in result.pages.values()) and all(result.pages[path].json_ld == page.json_ld for path,page in baseline.pages.items()),
    'visible_text_within_original_limit': len(result.home.visible_text) <= limit,
    'no_hidden_text_added': result.home.hidden_text == baseline.home.hidden_text,
    'all_nonhome_visible_content_unchanged': all(result.pages[path].visible_text == page.visible_text for path,page in baseline.pages.items() if path != '/'),
    'frozen_map_judge_and_normalizer_unchanged': all(digest(WRAPPER / path) == expected_hash for path,expected_hash in frozen.values()),
    'frozen_queries_unchanged': digest(ROOT / 'queries.txt') == 'f2440c27b9fa7596e902b5bc30a30130e10789564a75f661338742d40876d8ce',
    'production_r14_checkout_unchanged': git(PRODUCTION, 'rev-parse', 'HEAD') == change['current_production_commit'] and not git(PRODUCTION, 'status', '--porcelain'),
    'production_diff_only_index': production_changed == ['index.html'],
}
validation = {'checks': checks, 'errors': errors, 'inner_score': 'not computed',
    'visible_home_chars_before': len(baseline.home.visible_text), 'visible_home_chars_after': len(result.home.visible_text),
    'limit': limit, 'selection_seed_round': 9, 'parent_operation_count': 3,
    'scope_vs_seed': changed, 'scope_vs_current_production': production_changed,
    'browser_test': 'not performed; preserved markup and reused styles do not establish rendered layout or runtime behavior',
    **{name: digest(WRAPPER / value[0]) for name,value in frozen.items()}}
write('validation.json', validation)
write('combined-source-checks.json', {'component_source': components, 'second_backbone_source': second,
    'default_backbone_source': default, 'script_sha256': digest(SITE / 'script.js'),
    'facts': 'All added content comes verbatim from validated historical candidates and existing JS; combination score unknown'})
assert all(checks.values()), [name for name,passed in checks.items() if not passed]
ROOT.joinpath('candidate.patch').write_text(subprocess.check_output(['git', '-C', str(worktree), 'diff', '--unified=0'], text=True))
subprocess.run(['git', '-C', str(worktree), 'diff', '--check'], check=True)
subprocess.run(['git', '-C', str(worktree), 'add', '--', 'index.html'], check=True)
subprocess.run(['git', '-C', str(worktree), 'commit', '-m', 'R15: combine retained semantic H1 and static method/result references'], check=True)
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
assert pool['current_round'] == 15 and pool['selected_candidate_id'] == SELECTED
selected = next(p for p in pool['proposals'] if p['id'] == SELECTED)
selected.update({'status': change['state'], 'candidate_commit': commit, 'candidate_tree': tree,
    'wrapper_run_id': run['run_id'], 'branch': candidate['branch']})
write('candidate-pool-after.json', pool)
pool_path.write_text(json.dumps(pool, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({'run_id': run['run_id'], 'candidate_commit': commit, 'candidate_tree': tree,
    'checks_passed': len(checks), 'visible_chars': [len(baseline.home.visible_text), len(result.home.visible_text)],
    'outer_status': 'Unmeasured combination; R14 production unchanged'}, indent=2))
