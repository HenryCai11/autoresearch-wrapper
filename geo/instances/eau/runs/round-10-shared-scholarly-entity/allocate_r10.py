"""Allocate the isolated candidate and prepare a metadata-only graph patch."""
import copy
import html
import json
import os
import re
import subprocess
from pathlib import Path

from geo_eval.site import parse_html

ROOT = Path(__file__).resolve().parent
SITE = Path('/scratch/henrycai/eau-r10-20261016')
WRAPPER = Path('/project/aip-xiye17/henrycai/autoresearch-wrapper')
RUNNER = WRAPPER / 'skills/autoresearch-wrapper-run/run.sh'
FILES = ['index.html', 'method.html', 'paper.html', 'research-context.html']
BASE_URL = 'https://eau-meta-agent.github.io/'
ARTICLE_ID = BASE_URL + '#paper'
LD = re.compile(r'<script\s+type="application/ld\+json">\s*(.*?)\s*</script>', re.S)
run = json.loads(ROOT.joinpath('wrapper-run.json').read_text())


def write(name, value):
    ROOT.joinpath(name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def cli(*args, name, repo=SITE):
    environment = os.environ.copy()
    environment.pop('PYTHONPATH', None)
    result = subprocess.run(['bash', str(RUNNER), *args, '--repo', str(repo)], env=environment,
                            capture_output=True, text=True)
    ROOT.joinpath(name).write_text(result.stdout)
    ROOT.joinpath(name + '.stderr.txt').write_text(result.stderr)
    result.check_returncode()
    return result.stdout


assert not ROOT.joinpath('seed-record.json').exists(), 'Preparation is append-only; resume recorded state explicitly'
cli('evaluate', '--run-id', run['run_id'], '--candidate', 'seed', '--json', name='seed-evaluation.json')
cli('record', '--run-id', run['run_id'], '--candidate', 'seed', '--status', 'auto',
    '--description', 'Preserved R9 live outer baseline: 8/60 citations; 60 valid cells; inner ignored',
    '--json', name='seed-record.json')
candidate = json.loads(cli('allocate', '--run-id', run['run_id'], '--json', name='wrapper-candidate.json'))
worktree = Path(candidate['worktree_path'])
sources = {name: SITE.joinpath(name).read_text() for name in FILES}
old = {name: json.loads(LD.search(source).group(1)) for name, source in sources.items()}
assert all(len(LD.findall(source)) == 1 for source in sources.values())
assert all(value['identifier'] == 'arXiv:2610.16523' for value in old.values())
assert old['index.html']['author'] == old['paper.html']['author']
article = copy.deepcopy(old['index.html'])
article.pop('@context')
article.update({'@id': ARTICLE_ID,
                'headline': old['paper.html']['headline'],
                'datePublished': old['paper.html']['datePublished'],
                'mainEntityOfPage': {'@id': BASE_URL + '#webpage'}})
graphs, replacements = {}, {}
for name, source in sources.items():
    parsed = parse_html(source)
    canonical = BASE_URL if name == 'index.html' else BASE_URL + name
    assert parsed.canonical == canonical
    page = {'@type': 'WebPage', '@id': canonical + '#webpage', 'url': canonical,
            'name': html.unescape(re.search(r'<title>(.*?)</title>', source.split('</head>', 1)[0], re.S).group(1)), 'description': old[name]['description'],
            'mainEntity': {'@id': ARTICLE_ID}}
    for field in ['about', 'keywords']:
        if field in old[name]:
            page[field] = copy.deepcopy(old[name][field])
    graph = {'@context': 'https://schema.org', '@graph': [page, article]}
    replacement = '<script type="application/ld+json">\n' + '\n'.join(
        '  ' + line for line in json.dumps(graph, ensure_ascii=False, indent=2).splitlines()) + '\n  </script>'
    graphs[name] = graph
    replacements[name] = replacement
write('schema-before.json', old)
write('schema-after.json', graphs)
write('operations.json', {'operations': [{'op': 'replace_text', 'node': 'meta:schema',
    'before': LD.search(sources['index.html']).group(0), 'after': replacements['index.html']}]})
config, evidence = str(ROOT / 'config.json'), str(ROOT / 'r9-search-evidence.json')
cli('geo-graph', '--config', config, name='graph-before.json', repo=worktree)
cli('geo-prioritize', '--config', config, '--search-evidence', evidence, name='priorities.json', repo=worktree)
cli('geo-decide', '--config', config, '--search-evidence', evidence, name='decision.json', repo=worktree)
cli('geo-explore', '--config', config, '--search-evidence', evidence, name='exploration.json', repo=worktree)
cli('geo-apply', '--config', config, '--operations', str(ROOT / 'operations.json'), name='preview.json', repo=worktree)
cli('geo-apply', '--config', config, '--operations', str(ROOT / 'operations.json'), '--apply', name='applied.json', repo=worktree)

# The current geo-apply graph exposes the homepage schema but does not support
# replace_text on linked HTML assets. Do not change the wrapper for this site.
# Emit an exact three-file patch for the agent's apply_patch tool instead.
patch = ['*** Begin Patch']
for name in FILES[1:]:
    before = '  ' + LD.search(sources[name]).group(0)
    patch += ['*** Update File: ' + str(worktree / name), '@@']
    patch += ['-' + line for line in before.splitlines()]
    patch += ['+' + line for line in ('  ' + replacements[name]).splitlines()]
patch.append('*** End Patch')
ROOT.joinpath('support-schema.apply_patch').write_text('\n'.join(patch) + '\n')
print(json.dumps({'run_id': run['run_id'], 'worktree': str(worktree),
                  'article_id': ARTICLE_ID, 'next': 'Apply support-schema.apply_patch, then validate through Slurm.'}, indent=2))
