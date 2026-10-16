"""Test a visible two-line entity heading through geo-apply in a worktree."""
import hashlib
import json
import os
import subprocess
import sys
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlparse

from autoresearch_wrapper.geo import SectionParser
from geo_eval.site import load_site

ROOT = Path(__file__).resolve().parent
WRAPPER = Path('/project/aip-xiye17/henrycai/autoresearch-wrapper')
INSTANCE = WRAPPER / 'geo/instances/eau'
SITE = Path('/scratch/henrycai/eau-r12-20261016')
PRODUCTION = Path('/project/aip-xiye17/henrycai/eau-meta-agent.github.io')
RUNNER = WRAPPER / 'skills/autoresearch-wrapper-run/run.sh'
run = json.loads(ROOT.joinpath('wrapper-run.json').read_text())
change = json.loads(ROOT.joinpath('change.json').read_text())


def write(name, value):
    ROOT.joinpath(name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def cli(*args, name, repo=SITE):
    environment = os.environ.copy()
    environment.pop('PYTHONPATH', None)
    result = subprocess.run(['bash', str(RUNNER), *args, '--repo', str(repo)], env=environment,
                            capture_output=True, text=True)
    ROOT.joinpath(name).write_text(result.stdout)
    ROOT.joinpath(name + '.stderr.txt').write_text(result.stderr)
    result.check_returncode()
    return result.stdout


def sections(source):
    parser = SectionParser(source)
    parser.feed(source)
    return parser.sections


assert not ROOT.joinpath('wrapper-candidate.json').exists(), 'Do not allocate a second R12 candidate on retry'
cli('evaluate', '--run-id', run['run_id'], '--candidate', 'seed', '--json', name='seed-evaluation.json')
seed = json.loads(cli('record', '--run-id', run['run_id'], '--candidate', 'seed', '--status', 'auto',
    '--description', 'Preserved best R9 baseline: 8/60 citations, complete; R11 discard remains deployed, not selection threshold',
    '--json', name='seed-record.json'))
assert abs(seed['metric_value'] - 100 * 8 / 60) < 1e-9
candidate = json.loads(cli('allocate', '--run-id', run['run_id'], '--json', name='wrapper-candidate.json'))
worktree = Path(candidate['worktree_path'])
source = SITE.joinpath('index.html').read_text()
original_sections = sections(source)
before = '<h1 id="hero-title">Learning to<br>evolve, <em>together.</em></h1>'
after = '<h1 id="hero-title">EAU:<br><em>Co-evolution.</em></h1>'
assert source.count(before) == 1
write('heading-change.json', {'before': before, 'after': after,
    'facts': 'Existing EAU name and co-evolution topic; the full existing paper title remains in the adjacent subtitle and document metadata.',
    'layout_scope': 'Same h1 id, two lines separated by one br, and em styling; no CSS change. Not browser-validated.'})
write('operations.json', {'operations': [{'op': 'replace_text', 'node': 'file:index.html', 'before': before, 'after': after}]})
config, evidence = str(ROOT / 'config.json'), str(ROOT / 'r11-search-evidence.json')
for command, output in [('geo-graph', 'graph-before.json'), ('geo-prioritize', 'priorities.json'),
                        ('geo-decide', 'decision.json'), ('geo-explore', 'exploration.json')]:
    args = [command, '--config', config]
    if command != 'geo-graph':
        args += ['--search-evidence', evidence]
    cli(*args, name=output, repo=worktree)
cli('geo-apply', '--config', config, '--operations', str(ROOT / 'operations.json'), name='preview.json', repo=worktree)
cli('geo-apply', '--config', config, '--operations', str(ROOT / 'operations.json'), '--apply', name='applied.json', repo=worktree)
cli('geo-graph', '--config', config, name='graph-after.json', repo=worktree)


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
edited = worktree.joinpath('index.html').read_text()
new_sections = sections(edited)
baseline, result = load_site(str(SITE)), load_site(str(worktree))
changed = subprocess.check_output(['git', '-C', str(worktree), 'diff', '--name-only'], text=True).splitlines()
production_changed = subprocess.check_output(['git', '-C', str(worktree), 'diff', change['current_production_commit'], '--name-only'], text=True).splitlines()
limit = json.loads(INSTANCE.joinpath('map.json').read_text())['limits']['max_visible_chars']
frozen = {'knowledge_map_sha256': ('geo/instances/eau/map.json', '32be06bcafec6c3da9cf8360d86fa8e7154d6d05e1c46e598efd328c2d57973f'),
    'judge_sha256': ('geo_eval/discovery.py', '6bb1498e65e5cf065cc8e03e40007c73c32393e16f85a41d2395db76820613de'),
    'normalization_sha256': ('geo_eval/search_api.py', '8a2856dd9b69fe4b24c7b315f55ac6c98b7bcbd9063dd1093a11fba3e181d537')}
checks = {
    'only_index_changed_vs_best_r9_seed': changed == ['index.html'],
    'only_exact_h1_changed': edited == source.replace(before, after, 1),
    'h1_uses_existing_entity_and_topic_and_retains_id': edited.count(after) == 1 and before not in edited and 'aria-labelledby="hero-title"' in edited,
    'all_named_sections_unchanged_including_r7_overview': set(new_sections) == set(original_sections) and all(edited[new_sections[key][0]:new_sections[key][1]] == source[span[0]:span[1]] for key, span in original_sections.items()),
    'full_existing_paper_title_stays_in_hero_subtitle': '<p class="hero-subtitle">Environment–Agent–User Co-evolution<br>for Training User-Centric Agents</p>' in edited,
    'existing_two_line_br_and_em_structure_preserved': before.count('<br>') == after.count('<br>') == 1 and before.count('<em>') == after.count('<em>') == 1,
    'r9_static_results_preserved': edited[new_sections['results'][0]:new_sections['results'][1]] == source[original_sections['results'][0]:original_sections['results'][1]] and '<tbody id="results-table-body"><tr>' in edited,
    'all_head_bytes_including_schema_unchanged_vs_r9': edited.split('</head>', 1)[0] == source.split('</head>', 1)[0],
    'all_other_tracked_files_unchanged_vs_seed': changed == ['index.html'] and not subprocess.check_output(['git', '-C', str(worktree), 'ls-files', '--others', '--exclude-standard'], text=True).strip(),
    'local_links_fragments_and_unique_ids_valid': not errors,
    'one_home_h1': pages['index.html'].h1s == 1,
    'jsonld_valid_and_same_as_seed': all(not page.json_ld_errors for page in result.pages.values()) and all(result.pages[path].json_ld == page.json_ld for path, page in baseline.pages.items()),
    'visible_text_within_existing_limit': len(result.home.visible_text) <= limit,
    'no_hidden_text_added': result.home.hidden_text == baseline.home.hidden_text,
    'nonhome_visible_content_unchanged': all(result.pages[path].visible_text == page.visible_text for path, page in baseline.pages.items() if path != '/'),
    'frozen_map_judge_and_normalizer_unchanged': all(digest(WRAPPER / path) == expected for path, expected in frozen.values()),
    'query_set_unchanged': digest(ROOT / 'queries.txt') == 'f2440c27b9fa7596e902b5bc30a30130e10789564a75f661338742d40876d8ce',
    'current_r11_production_checkout_unchanged': subprocess.check_output(['git', '-C', str(PRODUCTION), 'rev-parse', 'HEAD'], text=True).strip() == change['current_production_commit'] and not subprocess.check_output(['git', '-C', str(PRODUCTION), 'status', '--porcelain'], text=True).strip(),
    'production_diff_has_only_index': production_changed == ['index.html'],
}
validation = {'checks': checks, 'errors': errors, 'inner_score': 'not computed',
    'visible_home_chars_before': len(baseline.home.visible_text), 'visible_home_chars_after': len(result.home.visible_text), 'limit': limit,
    'selection_seed': 'R9, not current R11 production',
    'scope_vs_seed': changed, 'scope_vs_current_production': production_changed,
    'browser_test': 'not performed; scripts/styles, heading id, br and em structure are unchanged; layout fit is not claimed as browser-tested',
    **{name: digest(WRAPPER / value[0]) for name, value in frozen.items()}}
write('validation.json', validation)
assert all(checks.values()), [name for name, passed in checks.items() if not passed]
ROOT.joinpath('candidate.patch').write_text(subprocess.check_output(['git', '-C', str(worktree), 'diff', '--unified=0'], text=True))
subprocess.run(['git', '-C', str(worktree), 'diff', '--check'], check=True)
subprocess.run(['git', '-C', str(worktree), 'add', '--', 'index.html'], check=True)
subprocess.run(['git', '-C', str(worktree), 'commit', '-m', 'R12: put EAU co-evolution identity in the visible main heading'], check=True)
commit = subprocess.check_output(['git', '-C', str(worktree), 'rev-parse', 'HEAD'], text=True).strip()
tree = subprocess.check_output(['git', '-C', str(worktree), 'rev-parse', 'HEAD^{tree}'], text=True).strip()
ROOT.joinpath('production-to-candidate.patch').write_text(subprocess.check_output(['git', '-C', str(worktree), 'diff', '--unified=0', change['current_production_commit'], commit], text=True))
guard = subprocess.run([sys.executable, str(ROOT / 'outer_metric.py')], cwd=worktree, capture_output=True, text=True)
assert guard.returncode == 2 and 'No live measurement' in guard.stderr
ROOT.joinpath('unpublished-metric-guard.txt').write_text(guard.stderr)
change.update({'state': 'validated_awaiting_deployment_approval', 'candidate_commit': commit, 'candidate_tree': tree,
    'wrapper_run_id': run['run_id'], 'candidate': candidate, 'production_changed_files': production_changed,
    'selection_seed_commit': change['base_production_commit'], 'selection_seed_tree': change['base_production_tree']})
write('change.json', change)
pool_path = INSTANCE / 'candidate-pool.json'
pool = json.loads(pool_path.read_text())
assert pool['current_round'] == 12 and pool['selected_candidate_id'] == 'homepage-descriptive-h1'
selected = next(p for p in pool['proposals'] if p['id'] == pool['selected_candidate_id'])
selected.update({'status': change['state'], 'candidate_commit': commit, 'candidate_tree': tree,
                 'wrapper_run_id': run['run_id'], 'branch': candidate['branch']})
write('candidate-pool-after.json', pool)
pool_path.write_text(json.dumps(pool, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({'run_id': run['run_id'], 'candidate_commit': commit, 'candidate_tree': tree,
    'checks_passed': len(checks), 'changed_vs_r9': changed, 'changed_vs_r11': production_changed,
    'outer_status': 'unmeasured; seed R9 replay is 8/60; current production unchanged'}, indent=2))
