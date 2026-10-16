"""Compare a repeated live R6 measurement without overwriting the first observation."""
import csv
import datetime as dt
import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path
from urllib.parse import urlparse

from geo_eval.discovery import URL_RE, build_discovery, judge_answers_file
from geo_eval.kmap import contains_any, load_map

ROOT = Path(__file__).resolve().parent
WRAPPER = Path('/project/aip-xiye17/henrycai/autoresearch-wrapper')
SITE = Path('/project/aip-xiye17/henrycai/eau-meta-agent.github.io')
PRIOR = WRAPPER / 'geo/instances/eau/runs/round-6-canonical-citation-entry/r6-live'
R5 = WRAPPER / 'geo/instances/eau/runs/round-6-canonical-citation-entry/r5-control'
plan = json.loads(ROOT.joinpath('measurement-plan.json').read_text())


def write(name, data):
    ROOT.joinpath(name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


queries = ROOT.joinpath('queries.txt').read_text().splitlines()
assert len(queries) == len(set(queries)) == 15
assert digest(ROOT / 'queries.txt') == plan['query_sha256']
assert ROOT.joinpath('search-map.json').read_bytes() == PRIOR.joinpath('search-map.json').read_bytes()
assert subprocess.check_output(['git', '-C', str(SITE), 'rev-parse', 'HEAD'], text=True).strip() == plan['production_commit_before']
assert subprocess.check_output(['git', '-C', str(SITE), 'rev-parse', 'HEAD^{tree}'], text=True).strip() == plan['production_tree']
assert ROOT.joinpath('origin-main-after.txt').read_text().split()[0] == plan['production_commit_before']
for name in ['production-index-before.html', 'production-index-after.html']:
    assert digest(ROOT / name) == plan['homepage_sha256']
    assert ROOT.joinpath(name).read_bytes() == SITE.joinpath('index.html').read_bytes()

codex = {}
for group in [1, 2]:
    for line in ROOT.joinpath(f'codex-group-{group}/answers.jsonl').read_text().splitlines():
        row = json.loads(line)
        assert row['query'] not in codex
        codex[row['query']] = row
assert set(codex) == set(queries)
ROOT.joinpath('codex-answers-complete.jsonl').write_text(''.join(json.dumps(codex[q], ensure_ascii=False) + '\n' for q in queries))
engines = {'gpt-web': 'gpt-web-answers.jsonl', 'codex-search': 'codex-answers-complete.jsonl',
           'tavily-search': 'tavily-answers.jsonl', 'exa-search': 'exa-answers.jsonl'}
kmap = load_map(ROOT / 'search-map.json')
probes, answers = [], {}
for engine, filename in engines.items():
    lines = ROOT.joinpath(filename).read_text().splitlines()
    assert len(lines) == 15
    assert {json.loads(line)['query'] for line in lines} == set(queries)
    probes.extend(judge_answers_file(kmap, lines, engine, 'Unchanged R6 delayed repeat; same frozen 15-query/four-engine protocol; no inner metric'))
    answers.update({(row['query'], engine): row for row in map(json.loads, lines)})
ROOT.joinpath('search-probes.jsonl').write_text(''.join(json.dumps(p, ensure_ascii=False) + '\n' for p in probes))
discovery = build_discovery(kmap, probes)
write('discovery.json', discovery.to_dict())
ROOT.joinpath('discovery.md').write_text(discovery.to_markdown() + '\n')
index = {(p['query'], p['engine']): p for p in probes}
rows, explicit = [], {}
for i, query in enumerate(queries):
    for engine in engines:
        probe, answer = index[(query, engine)], answers[(query, engine)]
        text = str(answer.get('text', ''))
        urls = list(dict.fromkeys(url.rstrip('.,;:!?*_') for url in URL_RE.findall(text)
                                 if urlparse(url.rstrip('.,;:!?*_')).netloc.lower() == 'eau-meta-agent.github.io'))
        explicit[(query, engine)] = urls
        rows.append({'query': query, 'tier': 'exact' if i < 5 else 'fuzzy' if i < 10 else 'broad', 'engine': engine,
                     'mention': contains_any(text, kmap.identity_terms), 'found': bool(probe.get('found')),
                     'site_cited': bool(probe.get('site_cited')), 'attributed': bool(probe.get('attributed')),
                     'rank': probe.get('rank'), 'reciprocal_rank': 1 / probe['rank'] if probe.get('rank') else 0.0,
                     'url': probe.get('url'), 'answer_empty': not bool(text.strip())})
with ROOT.joinpath('search-matrix.csv').open('w', newline='') as handle:
    writer = csv.DictWriter(handle, fieldnames=rows[0], lineterminator='\n')
    writer.writeheader()
    writer.writerows(rows)


def read_matrix(path):
    with path.open(newline='') as handle:
        matrix = list(csv.DictReader(handle))
    for row in matrix:
        for field in ['mention', 'found', 'site_cited', 'attributed', 'answer_empty']:
            row[field] = row[field] == 'True'
        row['reciprocal_rank'] = float(row['reciprocal_rank'])
        row['rank'] = int(row['rank']) if row['rank'] not in ['', 'None'] else None
        row['url'] = row['url'] if row['url'] not in ['', 'None'] else None
    return matrix


def stats(items):
    n = len(items)
    if not n:
        return {'n': 0, 'citation_rate': None, 'score': None}
    result = {'n': n, 'valid_responses': sum(not r['answer_empty'] for r in items),
              'project_citations': sum(r['site_cited'] for r in items),
              'mention_rate': sum(r['mention'] for r in items)/n,
              'found_rate': sum(r['found'] for r in items)/n,
              'citation_rate': sum(r['site_cited'] for r in items)/n,
              'attribution_rate': sum(r['attributed'] for r in items)/n,
              'mrr': sum(r['reciprocal_rank'] for r in items)/n}
    result['score'] = 100 * (.45*result['citation_rate'] + .25*result['attribution_rate'] + .20*result['mrr'] + .10*result['mention_rate'])
    return result


def compare(before, after):
    lookup = {(r['query'], r['engine']): r for r in before}
    pairs = [(lookup[(r['query'], r['engine'])], r) for r in after
             if not r['answer_empty'] and not lookup[(r['query'], r['engine'])]['answer_empty']]
    a, b = stats([p[0] for p in pairs]), stats([p[1] for p in pairs])
    fields = ['mention', 'found', 'site_cited', 'attributed', 'rank', 'url']
    changed = [{'query': x['query'], 'engine': x['engine'],
                'fields': {f: {'before': x[f], 'after': y[f]} for f in fields if x[f] != y[f]}}
               for x, y in pairs if any(x[f] != y[f] for f in fields)]
    return {'matched_valid_cells': len(pairs), 'before': a, 'after': b,
            'citation_delta_pp': 100*(b['citation_rate'] - a['citation_rate']) if pairs else None,
            'composite_delta': b['score'] - a['score'] if pairs else None,
            'citation_gains': sum(not x['site_cited'] and y['site_cited'] for x, y in pairs),
            'citation_losses': sum(x['site_cited'] and not y['site_cited'] for x, y in pairs),
            'cell_changes': changed}


before = read_matrix(PRIOR / 'search-matrix.csv')
assert len(before) == 60
old = json.loads(PRIOR.joinpath('summary.json').read_text())
assert abs(stats(before)['score'] - old['scheduled']['score']) < 1e-9
comparison = compare(before, rows)
write('comparison-vs-r6-immediate.json', comparison)
if R5.joinpath('search-matrix.csv').exists():
    write('comparison-vs-r5-control.json', compare(read_matrix(R5 / 'search-matrix.csv'), rows))
finished = dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')
started = dt.datetime.fromisoformat(plan['collection_started_at'].replace('Z', '+00:00'))
verified = dt.datetime.fromisoformat(plan['first_verified_served_at'].replace('Z', '+00:00'))
report = {**plan, 'summarized_at': finished, 'wait_since_first_verified_served_minutes': (started - verified).total_seconds()/60,
          'scheduled': stats(rows), 'valid_response': stats([r for r in rows if not r['answer_empty']]),
          'by_engine': {engine: stats([r for r in rows if r['engine'] == engine]) for engine in engines},
          'by_tier': {tier: stats([r for r in rows if r['tier'] == tier]) for tier in ['exact', 'fuzzy', 'broad']},
          'matched_valid_comparison': comparison,
          'explicit_project_url_cells': sum(bool(urls) for urls in explicit.values()),
          'complete': sum(not r['answer_empty'] for r in rows) == 60,
          'interpretation': 'A time-repeat of unchanged content, not a new candidate or causal estimate of waiting. A 13-minute wait is not a controlled recrawl experiment.',
          'original_run_unchanged': True}
write('summary.json', report)
write('explicit-project-urls.json', [{'query': q, 'engine': e, 'urls': urls} for (q,e),urls in explicit.items() if urls])
write('run.json', {key: report[key] for key in ['round', 'measurement_phase', 'collection_started_at', 'summarized_at',
      'first_verified_served_at', 'production_commit_before', 'production_tree', 'homepage_sha256', 'query_sha256', 'wait_since_first_verified_served_minutes']})
hash_paths = ['queries.txt', 'search-map.json', 'search-matrix.csv', *engines.values()]
write('integrity.json', {'sha256': {name: digest(ROOT / name) for name in hash_paths},
                        'judge_sha256': digest(WRAPPER / 'geo_eval/discovery.py'),
                        'normalization_sha256': digest(WRAPPER / 'geo_eval/search_api.py'),
                        'baseline_matrix_sha256': digest(PRIOR / 'search-matrix.csv'),
                        'baseline_matrix': str(PRIOR / 'search-matrix.csv')})
body = f'''# R6 延迟复测（不改页面）

线上版本保持 `{plan['production_commit_before']}`；采集前后公网首页字节一致。
{plan['collection_started_at']} 开始复测，距离首次确认 R6 上线约 {(started-verified).total_seconds()/60:.1f} 分钟。
同样的 15 查询 × 4 搜索引擎、参数和评判规则；不使用 inner metric。

| 引擎 | 首次引用 | 本次引用 | 本次有效响应 |
| --- | ---: | ---: | ---: |
'''
for engine in engines:
    first = old['by_engine'][engine]
    now = report['by_engine'][engine]
    body += f"| {engine} | {first['project_citations']}/15 | {now['project_citations']}/15 | {now['valid_responses']}/15 |\n"
body += f'''
总计：{old['scheduled']['project_citations']}/60 → {report['scheduled']['project_citations']}/60
（{100*old['scheduled']['citation_rate']:.2f}% → {100*report['scheduled']['citation_rate']:.2f}%）。
Outer composite：{old['scheduled']['score']:.2f} → {report['scheduled']['score']:.2f}。
Matched-valid：{comparison['matched_valid_cells']}/60；引用新增 {comparison['citation_gains']} 格、减少 {comparison['citation_losses']} 格。

本次有 {report['explicit_project_url_cells']}/60 格出现明确项目 URL。
主指标沿用旧 judge：裸项目域名也可算 `site_cited`，不等同于明确来源链接。
详见 `explicit-project-urls.json` 和逐格 `search-matrix.csv`。

这是同一页面在不同时间的搜索重复，不足以证明变化来自发布延迟或索引刷新。
约 13 分钟的等待也不能排除仍未 recrawl；如需检验索引滞后，应在更长间隔后保留相同协议继续测。
原始 R6 结果与 keep/discard 记录未覆盖；R7 未发布。
'''
ROOT.joinpath('REPORT.md').write_text(body)
print(json.dumps({key: report[key] for key in ['scheduled', 'by_engine', 'matched_valid_comparison',
      'explicit_project_url_cells', 'complete', 'wait_since_first_verified_served_minutes']}, ensure_ascii=False, indent=2))
