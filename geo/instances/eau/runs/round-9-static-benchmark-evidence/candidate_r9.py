"""Use the existing renderer as the data oracle, then edit only section:results."""
import hashlib
import json
import os
import shutil
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
SITE = Path('/scratch/henrycai/eau-r9-20261016')
RUNNER = WRAPPER / 'skills/autoresearch-wrapper-run/run.sh'
run = json.loads(ROOT.joinpath('wrapper-run.json').read_text())
environment = os.environ.copy()
environment.pop('PYTHONPATH', None)


def write(name, data):
    ROOT.joinpath(name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def cli(*args, output, repo=SITE):
    result = subprocess.run(['bash', str(RUNNER), *args, '--repo', str(repo)], env=environment,
                            capture_output=True, text=True)
    ROOT.joinpath(output).write_text(result.stdout)
    ROOT.joinpath(output + '.stderr.txt').write_text(result.stderr)
    if result.returncode:
        print(result.stderr)
        result.check_returncode()
    return result.stdout


if not ROOT.joinpath('seed-record.json').exists():
    cli('evaluate', '--run-id', run['run_id'], '--candidate', 'seed', '--json', output='seed-evaluation.json')
    cli('record', '--run-id', run['run_id'], '--candidate', 'seed', '--status', 'auto',
        '--description', 'Preserved R8 live outer baseline: 6/60 citations; 60 valid cells; inner ignored',
        '--json', output='seed-record.json')
if ROOT.joinpath('wrapper-candidate.json').exists():
    allocated = json.loads(ROOT.joinpath('wrapper-candidate.json').read_text())
else:
    allocated = json.loads(cli('allocate', '--run-id', run['run_id'], '--json', output='wrapper-candidate.json'))
worktree = Path(allocated['worktree_path'])
node_command = shutil.which('node')
assert node_command, 'Load the discovered Node.js module in this Slurm job'
oracle = json.loads(subprocess.check_output([node_command, str(ROOT / 'render_oracle.js'), str(SITE / 'script.js')], text=True))
write('runtime-render-oracle.json', oracle)
default = oracle['qwen3']
source = worktree.joinpath('index.html').read_text()
parser = SectionParser(source)
parser.feed(source)
start, end = parser.sections['results']
original = source[start:end]
replacement = original
for before, after in [
    ('<div class="chart-grid" id="result-charts" aria-live="polite"></div>',
     '<div class="chart-grid" id="result-charts" aria-live="polite">' + default['charts'] + '</div>'),
    ('<tbody id="results-table-body"></tbody>', '<tbody id="results-table-body">' + default['table'] + '</tbody>'),
    ('<noscript><p>Enable JavaScript to explore the model comparison. On Qwen3-4B, eau scores 0.623 on UserGym, 0.600 on ColBench task success, and 0.627 overall. The source tables are included in the downloadable manuscript.</p></noscript>',
     '<noscript><p>Showing the Qwen3-4B results. Enable JavaScript to switch the policy backbone. The source tables are included in the downloadable manuscript.</p></noscript>'),
]:
    assert replacement.count(before) == 1
    replacement = replacement.replace(before, after, 1)
write('operations.json', {'operations': [{'op': 'edit', 'node': 'section:results', 'html': replacement}]})
config, evidence = str(ROOT / 'config.json'), str(ROOT / 'r8-search-evidence.json')
cli('geo-graph', '--config', config, output='graph-before.json', repo=worktree)
cli('geo-prioritize', '--config', config, '--search-evidence', evidence, output='priorities.json', repo=worktree)
cli('geo-decide', '--config', config, '--search-evidence', evidence, output='decision.json', repo=worktree)
cli('geo-explore', '--config', config, '--search-evidence', evidence, output='exploration.json', repo=worktree)
cli('geo-apply', '--config', config, '--operations', str(ROOT / 'operations.json'), output='preview.json', repo=worktree)
cli('geo-apply', '--config', config, '--operations', str(ROOT / 'operations.json'), '--apply', output='applied.json', repo=worktree)
cli('geo-graph', '--config', config, output='graph-after.json', repo=worktree)


class Elements(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.ids, self.refs, self.h1s, self.cards = [], [], 0, 0
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if 'id' in attrs:
            self.ids.append(attrs['id'])
        self.h1s += tag == 'h1'
        self.cards += tag == 'article' and attrs.get('class') == 'chart-card'
        if tag in ['a', 'link', 'script', 'img']:
            ref = attrs.get('href') or attrs.get('src')
            if ref:
                self.refs.append(ref)


pages = {p.name: Elements(p.read_text()) for p in worktree.glob('*.html')}
errors = []
for name, page in pages.items():
    if any(n > 1 for n in Counter(page.ids).values()):
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
home = worktree.joinpath('index.html').read_text()
site = load_site(str(worktree))
baseline = load_site(str(SITE))
changed = subprocess.check_output(['git', '-C', str(worktree), 'diff', '--name-only'], text=True).splitlines()
unchanged = [name for name in subprocess.check_output(['git', '-C', str(SITE), 'ls-files'], text=True).splitlines() if name != 'index.html']
limit = json.loads(INSTANCE.joinpath('map.json').read_text())['limits']['max_visible_chars']
paper = worktree.joinpath('paper.html').read_text()
table_fragment = '<tbody id="results-table-body">' + default['table'] + '</tbody>'
checks = {
    'only_index_changed': changed == ['index.html'],
    'only_results_section_changed': home == source[:start] + replacement + source[end:],
    'all_other_files_byte_identical': all((SITE / name).read_bytes() == (worktree / name).read_bytes() for name in unchanged),
    'metadata_unchanged': home.split('</head>')[0] == source.split('</head>')[0],
    'local_links_and_unique_ids_valid': not errors,
    'one_home_h1': pages['index.html'].h1s == 1,
    'jsonld_valid': all(not p.json_ld_errors for p in site.pages.values()),
    'visible_text_within_existing_limit': len(site.home.visible_text) <= limit,
    'default_static_cards_equal_existing_js_renderer': default['charts'] in home and pages['index.html'].cards == 3,
    'default_static_table_equal_existing_js_renderer': table_fragment in home and default['table'].count('<tr') == 9,
    'default_caption_matches_renderer': default['caption'] in home,
    'both_runtime_models_and_switch_back_checked': oracle['renderer_switch_checks_passed'],
    'headline_eau_numbers_match_existing_paper_page': all(number in paper and number in default['table'] for number in ['0.623', '0.600', '0.627']),
    'default_model_and_client_bootstrap_unchanged': 'data-model="qwen3" aria-pressed="true"' in home and
        "renderResults('qwen3');" in worktree.joinpath('script.js').read_text(),
}
write('validation.json', {'checks': checks, 'errors': errors, 'inner_score': 'not computed',
    'visible_home_chars_before': len(baseline.home.visible_text), 'visible_home_chars_after': len(site.home.visible_text),
    'limit': limit, 'renderer_test_scope': oracle['method'], 'source_js_sha256': digest(SITE / 'script.js'),
    'paper_sha256': digest(SITE / 'paper.html'), 'knowledge_map_sha256': digest(INSTANCE / 'map.json'),
    'judge_sha256': digest(WRAPPER / 'geo_eval/discovery.py'), 'normalization_sha256': digest(WRAPPER / 'geo_eval/search_api.py')})
assert all(checks.values()), checks
ROOT.joinpath('candidate.patch').write_text(subprocess.check_output(['git', '-C', str(worktree), 'diff', '--unified=0'], text=True))
subprocess.run(['git', '-C', str(worktree), 'diff', '--check'], check=True)
subprocess.run(['git', '-C', str(worktree), 'add', '--', 'index.html'], check=True)
subprocess.run(['git', '-C', str(worktree), 'commit', '-m', 'R9: pre-render existing default benchmark charts and table'], check=True)
commit = subprocess.check_output(['git', '-C', str(worktree), 'rev-parse', 'HEAD'], text=True).strip()
tree = subprocess.check_output(['git', '-C', str(worktree), 'rev-parse', 'HEAD^{tree}'], text=True).strip()
guard = subprocess.run([sys.executable, str(ROOT / 'outer_metric.py')], cwd=worktree, capture_output=True, text=True)
assert guard.returncode == 2 and 'No live measurement' in guard.stderr
ROOT.joinpath('unpublished-metric-guard.txt').write_text(guard.stderr)
change = json.loads(ROOT.joinpath('change.json').read_text())
change.update({'state': 'validated_awaiting_deployment_approval', 'candidate_commit': commit, 'candidate_tree': tree,
               'wrapper_run_id': run['run_id'], 'candidate': allocated})
write('change.json', change)
pool_path = INSTANCE / 'candidate-pool.json'
pool = json.loads(pool_path.read_text())
assert pool['selected_candidate_id'] == 'static-benchmark-evidence'
selected = next(item for item in pool['proposals'] if item['id'] == pool['selected_candidate_id'])
selected.update({'status': 'validated_awaiting_deployment_approval', 'candidate_commit': commit,
                 'candidate_tree': tree, 'wrapper_run_id': run['run_id'], 'branch': allocated['branch']})
write('candidate-pool-after.json', pool)
pool_path.write_text(json.dumps(pool, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({'run_id': run['run_id'], 'candidate_commit': commit, 'candidate_tree': tree,
                  'checks': checks, 'outer_metric': 'unmeasured until approved deployment'}, indent=2))
