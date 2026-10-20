"""Summarize R21 against original R18 after all three changed resources match."""
import csv
import datetime as dt
import hashlib
import json
import shutil
import subprocess
from pathlib import Path
from urllib.parse import urlparse

from geo_eval.discovery import URL_RE, build_discovery, judge_answers_file
from geo_eval.kmap import contains_any, load_map

ROOT = Path('/scratch/henrycai/geo-runs/eau-r21-20261020')
LIVE = ROOT / 'r21-live'
CONTROL = ROOT / 'control'
WRAPPER = Path('/project/aip-xiye17/henrycai/autoresearch-wrapper')
SITE = Path('/project/aip-xiye17/henrycai/eau-meta-agent.github.io')
queries = ROOT.joinpath('queries.txt').read_text().splitlines()
query_hash = hashlib.sha256(ROOT.joinpath('queries.txt').read_bytes()).hexdigest()
assert len(queries) == len(set(queries)) == 15
candidate = json.loads(ROOT.joinpath('wrapper-candidate.json').read_text())
candidate_tree = subprocess.check_output(['git', '-C', candidate['worktree_path'], 'rev-parse', 'HEAD^{tree}'], text=True).strip()
production_tree = subprocess.check_output(['git', '-C', str(SITE), 'rev-parse', 'HEAD^{tree}'], text=True).strip()
production_commit = subprocess.check_output(['git', '-C', str(SITE), 'rev-parse', 'HEAD'], text=True).strip()
assert production_tree == candidate_tree
deployment = json.loads(LIVE.joinpath('deployment.json').read_text())
assert deployment['production_merge_commit'] == production_commit
assert deployment['production_tree'] == production_tree
for name in json.loads(ROOT.joinpath('change.json').read_text())['production_changed_files']:
    for phase in ['before', 'after']:
        served = LIVE / f'served-{phase}' / name
        assert served.read_bytes() == SITE.joinpath(name).read_bytes()
        assert hashlib.sha256(served.read_bytes()).hexdigest() == deployment['resource_sha256'][name]
for phase in ['before', 'after']:
    assert LIVE.joinpath(f'origin-main-{phase}.txt').read_text().split()[0] == production_commit
validation = json.loads(ROOT.joinpath('validation.json').read_text())
assert hashlib.sha256(WRAPPER.joinpath('geo_eval/discovery.py').read_bytes()).hexdigest() == validation['judge_sha256']
assert hashlib.sha256(WRAPPER.joinpath('geo_eval/search_api.py').read_bytes()).hexdigest() == validation['normalization_sha256']
assert ROOT.joinpath('search-map.json').read_bytes() == CONTROL.joinpath('search-map.json').read_bytes()

def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')

codex = {}
codex_rows = 0
for path in [LIVE / 'codex-group-1/answers.jsonl', LIVE / 'codex-group-2/answers.jsonl']:
    for line in path.read_text().splitlines():
        row = json.loads(line)
        codex_rows += 1
        assert row['query'] not in codex, 'Duplicate Codex query'
        codex[row['query']] = row
assert codex_rows == 15 and set(codex) == set(queries)
LIVE.joinpath('codex-answers-complete.jsonl').write_text(''.join(json.dumps(codex[q], ensure_ascii=False) + '\n' for q in queries))
for name in ['queries.txt', 'search-map.json']:
    shutil.copy2(ROOT / name, LIVE / name)
kmap = load_map(LIVE / 'search-map.json')
ENGINES = {'gpt-web': 'gpt-web-answers.jsonl', 'codex-search': 'codex-answers-complete.jsonl',
           'tavily-search': 'tavily-answers.jsonl', 'exa-search': 'exa-answers.jsonl'}
probes, answers = [], {}
for engine, name in ENGINES.items():
    lines = LIVE.joinpath(name).read_text().splitlines()
    assert len(lines) == 15
    assert {json.loads(line)['query'] for line in lines} == set(queries)
    assert all(json.loads(line).get('status') == 'ok' for line in lines), f'{engine}: invalid response status'
    probes.extend(judge_answers_file(kmap, lines, engine, 'R21 immediate post-deployment measurement; deployed all three changed resources byte-verified; frozen queries/settings; preserved R18 12/60 selection control; no inner metric'))
    answers.update({(r['query'], engine): r for r in map(json.loads, lines)})
LIVE.joinpath('search-probes.jsonl').write_text(''.join(json.dumps(p, ensure_ascii=False) + '\n' for p in probes))
matrix = build_discovery(kmap, probes)
write_json(LIVE / 'discovery.json', matrix.to_dict())
LIVE.joinpath('discovery.md').write_text(matrix.to_markdown() + '\n')
probe_index = {(p['query'], p['engine']): p for p in probes}
tiers = {q: ('exact' if i < 5 else 'fuzzy' if i < 10 else 'broad') for i, q in enumerate(queries)}
rows = []
for query in queries:
    for engine in ENGINES:
        p, answer = probe_index[(query, engine)], answers[(query, engine)]
        text = str(answer.get('text', ''))
        rows.append({'query': query, 'tier': tiers[query], 'engine': engine,
                     'mention': contains_any(text, kmap.identity_terms), 'found': bool(p.get('found')),
                     'site_cited': bool(p.get('site_cited')), 'attributed': bool(p.get('attributed')),
                     'rank': p.get('rank'), 'reciprocal_rank': 1 / p['rank'] if p.get('rank') else 0.0,
                     'url': p.get('url'), 'answer_empty': not bool(text.strip())})
with LIVE.joinpath('search-matrix.csv').open('w', newline='') as handle:
    writer = csv.DictWriter(handle, fieldnames=rows[0].keys(), lineterminator='\n')
    writer.writeheader()
    writer.writerows(rows)

WEIGHTS = {'citation_rate': .45, 'attribution_rate': .25, 'mrr': .20, 'mention_rate': .10}
def stats(items):
    n = len(items)
    if not n:
        return {'n': 0, 'score': None, 'citation_rate': None}
    result = {'n': n, 'valid_responses': sum(not r['answer_empty'] for r in items),
              'project_citations': sum(r['site_cited'] for r in items),
              'mention_rate': sum(r['mention'] for r in items)/n,
              'found_rate': sum(r['found'] for r in items)/n,
              'citation_rate': sum(r['site_cited'] for r in items)/n,
              'attribution_rate': sum(r['attributed'] for r in items)/n,
              'mrr': sum(r['reciprocal_rank'] for r in items)/n}
    result['score'] = 100 * sum(result[k]*w for k,w in WEIGHTS.items())
    return result

baseline = []
for row in csv.DictReader(CONTROL.joinpath('search-matrix.csv').open()):
    for field in ['mention', 'found', 'site_cited', 'attributed', 'answer_empty']:
        row[field] = row[field] == 'True'
    row['reciprocal_rank'] = float(row['reciprocal_rank'])
    baseline.append(row)
before = {(r['query'], r['engine']): r for r in baseline}
pairs = [(before[(r['query'], r['engine'])], r) for r in rows
         if not r['answer_empty'] and not before[(r['query'], r['engine'])]['answer_empty']]
paired_before, paired_after = stats([p[0] for p in pairs]), stats([p[1] for p in pairs])
all_stats = stats(rows)
valid_stats = stats([r for r in rows if not r['answer_empty']])
project_url_evidence = []
for (query, engine), answer in answers.items():
    urls = list(dict.fromkeys(url.rstrip('.,;:!?*_') for url in URL_RE.findall(str(answer.get('text', '')))
                             if urlparse(url.rstrip('.,;:!?*_')).netloc.lower() == 'eau-meta-agent.github.io'))
    if urls:
        project_url_evidence.append({'query': query, 'engine': engine, 'urls': urls})
write_json(LIVE / 'explicit-project-urls.json', project_url_evidence)
support_paths = {'/method.html', '/paper.html', '/research-context.html', '/llms.txt'}
support_cells = [item for item in project_url_evidence if any(urlparse(url).path in support_paths for url in item['urls'])]
complete = all_stats['valid_responses'] == 60
verdict = ('keep' if all_stats['citation_rate'] > stats(baseline)['citation_rate'] else 'discard') if complete else 'inconclusive_tool_failures'
report = {
    'round': 21, 'experiment_id': 'eau-live-geo-r21-2026-10', 'change_id': 'r21-descriptive-static-evidence-combination',
    'production_merge_commit': production_commit, 'production_tree': production_tree,
    'production_url': 'https://eau-meta-agent.github.io/', 'measured_at': dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds'),
    'measurement_phase': 'immediate_post_deployment', 'query_count': 15, 'query_sha256': query_hash,
    'selection_policy': 'outer-only; primary project-domain citation rate; inner ignored',
    'scheduled': all_stats, 'valid_response': valid_stats,
    'by_engine': {e: stats([r for r in rows if r['engine'] == e]) for e in ENGINES},
    'by_tier': {t: stats([r for r in rows if r['tier'] == t]) for t in ['exact', 'fuzzy', 'broad']},
    'explicit_project_url_cells': sum(bool(r['url']) for r in rows),
    'explicit_support_page_url_cells': len(support_cells),
    'support_page_url_evidence': support_cells,
    'citation_transitions': {
        'gained': [{'query': x['query'], 'engine': x['engine']} for x, y in pairs if not x['site_cited'] and y['site_cited']],
        'lost': [{'query': x['query'], 'engine': x['engine']} for x, y in pairs if x['site_cited'] and not y['site_cited']],
    },
    'baseline_reference': 'Reused R18 live 60-cell measurement completed 2026-10-19T09:14:05Z; no new control collection',
    'matched_valid_comparison': {'baseline': paired_before, 'r21': paired_after,
                                'citation_delta': paired_after['citation_rate']-paired_before['citation_rate'],
                                'composite_delta': paired_after['score']-paired_before['score']},
    'decision': verdict,
    'limitations': ['An immediate single-sample search observation does not establish causal lift.',
                    'Search engines may still serve pre-deployment indexed copies; repeat after recrawling.',
                    'Provider/tool outputs are not directly interchangeable with consumer chat-app products.'],
}
write_json(LIVE / 'summary.json', report)
write_json(LIVE / 'run.json', {k: report[k] for k in ['experiment_id','round','change_id','production_merge_commit','production_tree','production_url','measured_at','measurement_phase','query_sha256']})
write_json(LIVE / 'comparison-vs-r18.json', report['matched_valid_comparison'])

registry = json.loads(ROOT.joinpath('outer-measurements.json').read_text())
assert not any(r['deployed_tree'] == production_tree for r in registry['measurements'])
registry['measurements'].append({'label': 'r21-immediate-live', 'deployed_commit': production_commit,
                               'deployed_tree': production_tree, 'query_sha256': query_hash,
                               'matrix': 'r21-live/search-matrix.csv',
                               'matrix_sha256': hashlib.sha256(LIVE.joinpath('search-matrix.csv').read_bytes()).hexdigest(),
                               'verification': 'Before/after deployed all three changed resources equal the merged R21 checkout and exact candidate tree.'})
write_json(ROOT / 'outer-measurements.json', registry)
write_json(LIVE / 'outer-measurements-after-r21.json', registry)
print(json.dumps(report, ensure_ascii=False, indent=2))
