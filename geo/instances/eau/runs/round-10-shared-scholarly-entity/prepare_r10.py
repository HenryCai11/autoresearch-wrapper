"""Lock R10's existing candidate-pool proposal and unchanged outer protocol."""
import datetime as dt
import hashlib
import json
import os
import subprocess
from pathlib import Path

from geo_eval.discovery import URL_RE

ROOT = Path(__file__).resolve().parent
WRAPPER = Path('/project/aip-xiye17/henrycai/autoresearch-wrapper')
INSTANCE = WRAPPER / 'geo/instances/eau'
SITE = Path('/scratch/henrycai/eau-r10-20261016')
RUNNER = WRAPPER / 'skills/autoresearch-wrapper-run/run.sh'
BASE = '52dee0ba78885b9a3028760ba8d9cfc749a6c2e7'
TREE = '5ebd5d1c28e00690d58caafa0edfe066ae5307d7'
FILES = ['index.html', 'method.html', 'paper.html', 'research-context.html']


def write(name, data):
    ROOT.joinpath(name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def cli(*args, output):
    environment = os.environ.copy()
    environment.pop('PYTHONPATH', None)
    result = subprocess.run(['bash', str(RUNNER), *args, '--repo', str(SITE)], env=environment,
                            capture_output=True, text=True)
    ROOT.joinpath(output).write_text(result.stdout)
    ROOT.joinpath(output + '.stderr.txt').write_text(result.stderr)
    if result.returncode:
        print(result.stderr)
        result.check_returncode()
    return result.stdout


assert subprocess.check_output(['git', '-C', str(SITE), 'rev-parse', 'HEAD'], text=True).strip() == BASE
assert subprocess.check_output(['git', '-C', str(SITE), 'rev-parse', 'HEAD^{tree}'], text=True).strip() == TREE
assert ROOT.joinpath('r9-production-index.html').read_bytes() == SITE.joinpath('index.html').read_bytes()
query_hash = digest(ROOT / 'queries.txt')
assert query_hash == 'f2440c27b9fa7596e902b5bc30a30130e10789564a75f661338742d40876d8ce'
queries = ROOT.joinpath('queries.txt').read_text().splitlines()
control = json.loads(ROOT.joinpath('r9-control/summary.json').read_text())
assert control['production_tree'] == TREE and control['scheduled']['valid_responses'] == 60
write('outer-measurements.json', {'measurements': [{
    'label': 'r9-live-reused-control', 'deployed_commit': BASE, 'deployed_tree': TREE,
    'measured_at': control['measured_at'], 'query_sha256': query_hash,
    'matrix': 'r9-control/search-matrix.csv', 'matrix_sha256': digest(ROOT / 'r9-control/search-matrix.csv'),
    'verification': 'Current production main is still R9; homepage bytes equal the R9 checkout. Original deployment proof is preserved with the control.',
}]})
pool_path = INSTANCE / 'candidate-pool.json'
pool_hash = digest(pool_path)
pool = json.loads(pool_path.read_text())
assert {entry['id'] for entry in pool['history']} == {f'r{i}' for i in range(10)}
write('candidate-pool-before.json', pool)
selected = next(item for item in pool['proposals'] if item['id'] == 'shared-scholarly-entity')
assert not selected.get('measured', False)
selected.update({'round': 10, 'change_id': 'r10-shared-scholarly-entity', 'status': 'selected_preparing',
    'measured': False, 'files': FILES, 'base_commit': BASE, 'parents': ['r1', 'r4', 'r8', 'r9'],
    'module_dependencies': ['index.html: existing project identity and author record', 'paper.html: existing scholarly metadata', 'method.html and research-context.html: distinct reference-page descriptions'],
    'scope': 'Replace only the JSON-LD block in four pages: one stable shared ScholarlyArticle @id, separate WebPage nodes, explicit mainEntity/mainEntityOfPage references. Retain visible content and all runtime behavior.',
    'reason_selected': 'All four pages describe the same paper as independent anonymous ScholarlyArticle objects with different page URLs. R9 supplies five explicit homepage URLs but no support-page URLs. Test a coherent shared identity without changing factual content, while retaining the R9 static results and R8 reference routes.',
    'alternatives_deferred': ['reference-cluster-without-r7', 'external-paper-link-audit'],
    'interpretation': 'This is an unranked controlled local test, not predicted citation lift. Do not add historical module scores.'})
pool['current_round'] = 10
pool['selected_candidate_id'] = selected['id']
pool['updated_at'] = dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')
policy = {
    'primary_metric': 'live_project_citation_rate', 'goal': 'maximize',
    'definition': '100 * frozen geo_eval site_cited cells / 60; bare project-domain occurrences count under the existing judge.',
    'engines': ['gpt-web', 'codex-search', 'tavily-search', 'exa-search'],
    'validity': 'All 60 frozen query-engine cells must return valid responses for automatic ranking.',
    'inner_metric': 'not computed and not used',
    'baseline': 'Preserved R9 immediate live observation at 2026-10-16T13:09:24Z: 8/60 citations, 30.25 composite. This is reused, not a new R10 control search.',
    'deployment': 'Require explicit R10 publication approval, all four edited resources byte-verified, and real four-engine observations before candidate evaluation.',
    'history': 'Retain discarded candidates and queued combinations; measure combinations rather than infer their scores.',
    'limitations': 'A single immediate sample with a historical control cannot establish a causal effect; search variation and indexing lag remain possible.',
}
write('outer-only-policy.json', policy)
pool['policy'] = policy
config = {
    'site_url': 'https://eau-meta-agent.github.io/', 'paper_url': 'https://arxiv.org/abs/2610.16523',
    'repo_url': 'https://github.com/eau-meta-agent/eau-meta-agent.github.io',
    'platforms': {engine: .25 for engine in policy['engines']},
    'queries': [{'id': f'Q{i:02d}', 'text': query} for i, query in enumerate(queries, 1)],
    'interventions': [
        {'id': 'r10-shared-scholarly-entity', 'candidate_id': 'r10-shared-scholarly-entity',
         'nodes': ['meta:schema', 'file:method.html', 'file:paper.html', 'file:research-context.html'],
         'source_url': 'https://eau-meta-agent.github.io/', 'link_state': 'present',
         'link_evidence_url': 'https://eau-meta-agent.github.io/', 'change_kind': 'node',
         'local_state': 'Four anonymous ScholarlyArticle records have different page URLs and no shared entity @id.',
         'hypothesis': selected['hypothesis'], 'candidate_arms': [
            {'id': p['id'], 'status': p['status'], 'hypothesis': p['hypothesis']} for p in pool['proposals']]},
        {'id': 'external-paper-link-audit', 'nodes': ['external:paper-backlink'],
         'source_url': 'https://arxiv.org/abs/2610.16523', 'link_state': 'unknown',
         'change_kind': 'edge', 'owner': 'paper author',
         'hypothesis': 'Any externally controlled paper edit requires separate authority; no external edit is part of R10.'},
    ],
}
write('config.json', config)
engine_files = {'gpt-web': 'gpt-web-answers.jsonl', 'codex-search': 'codex-answers-complete.jsonl', 'tavily-search': 'tavily-answers.jsonl', 'exa-search': 'exa-answers.jsonl'}
answers = {engine: {r['query']: r for r in map(json.loads, ROOT.joinpath('r9-control', name).read_text().splitlines())} for engine, name in engine_files.items()}
write('r9-search-evidence.json', {'tool': 'R9 saved four-engine responses (not new R10 probes)',
    'result_scope': 'Displayed source URLs, not a top-ten rank or predicted lift',
    'observations': [{'query_id': f'Q{i:02d}',
        'result_urls': list(dict.fromkeys(u.rstrip('.,;:!?*_') for engine in engine_files for u in URL_RE.findall(answers[engine][q]['text']))),
        'by_engine': {engine: list(dict.fromkeys(u.rstrip('.,;:!?*_') for u in URL_RE.findall(answers[engine][q]['text']))) for engine in engine_files},
        'raw_file': 'r9-control/gpt-web-answers.jsonl',
        'raw_files': {engine: 'r9-control/' + name for engine, name in engine_files.items()}} for i, q in enumerate(queries, 1)]})
write('change.json', {'round': 10, 'change_id': 'r10-shared-scholarly-entity', 'pool_candidate_id': selected['id'],
    'state': 'preparing', 'files': FILES, 'graph_nodes': ['meta:schema', 'file:method.html', 'file:paper.html', 'file:research-context.html'],
    'base_production_commit': BASE, 'base_production_tree': TREE, 'parents': selected['parents'],
    'hypothesis': selected['hypothesis'], 'selection': policy,
    'source_of_existing_data': {name: digest(SITE / name) for name in FILES},
    'knowledge_map_sha256': digest(INSTANCE / 'map.json'),
    'unchanged': ['all visible HTML and body bytes', 'R9 static benchmark results', 'all runtime JavaScript', 'styles', 'all non-JSON-LD metadata', 'other files', 'knowledge map', 'query set', 'judge', 'engine settings'],
    'technical_references': ['https://schema.org/mainEntity', 'https://schema.org/mainEntityOfPage', 'https://www.w3.org/TR/json-ld11/#node-identifiers']})
cli('scan', '--no-interactive', output='wrapper-scan.txt')
cli('configure', '--part', 'index.html', '--metric', 'live_project_citation_rate', '--metric-goal', 'maximize',
    '--metric-command', f'python3 {ROOT / "outer_metric.py"}', '--mode', 'sequential', '--rounds', '1',
    '--metric-timeout', '120', '--no-interactive', output='wrapper-configure.txt')
run = json.loads(cli('run', '--part', 'index.html', '--no-interactive', '--json', output='wrapper-run.json'))
write('candidate-pool-selected.json', pool)
assert digest(pool_path) == pool_hash, 'Concurrent ledger changes: preserve them before updating'
pool_path.write_text(json.dumps(pool, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({'run': run, 'selected_pool_candidate': selected['id'], 'baseline_citations': '8/60',
                  'history_count': len(pool['history']), 'inner_score': 'not computed'}, indent=2))
