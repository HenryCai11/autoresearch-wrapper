"""Select a retained combination on the best fully observed seed, not latest discard."""
import copy
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
SITE = Path('/scratch/henrycai/eau-r11-20261016')
PRODUCTION = Path('/project/aip-xiye17/henrycai/eau-meta-agent.github.io')
RUNNER = WRAPPER / 'skills/autoresearch-wrapper-run/run.sh'
BASE = '52dee0ba78885b9a3028760ba8d9cfc749a6c2e7'
TREE = '5ebd5d1c28e00690d58caafa0edfe066ae5307d7'
LIVE = 'b70597085286d4ff4c2d3de78f25d95581835b98'
LIVE_TREE = '14fdd73cd91dc01843dbe6a57b8f172cd249ea98'
RESTORE = 'e6b74d333b09c30619d5c3c61c95fa066ee50188'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(name, value):
    ROOT.joinpath(name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def git(repo, *args):
    return subprocess.check_output(['git', '-C', str(repo), *args], text=True).strip()


def cli(*args, name):
    environment = os.environ.copy()
    environment.pop('PYTHONPATH', None)
    result = subprocess.run(['bash', str(RUNNER), *args, '--repo', str(SITE)], env=environment,
                            capture_output=True, text=True)
    ROOT.joinpath(name).write_text(result.stdout)
    ROOT.joinpath(name + '.stderr.txt').write_text(result.stderr)
    result.check_returncode()
    return result.stdout


assert git(SITE, 'rev-parse', 'HEAD') == BASE and git(SITE, 'rev-parse', 'HEAD^{tree}') == TREE
assert git(PRODUCTION, 'rev-parse', 'HEAD') == LIVE and git(PRODUCTION, 'rev-parse', 'HEAD^{tree}') == LIVE_TREE
assert not git(SITE, 'status', '--porcelain') and not git(PRODUCTION, 'status', '--porcelain')
assert ROOT.joinpath('r10-production-index.html').read_bytes() == PRODUCTION.joinpath('index.html').read_bytes()
query_hash = digest(ROOT / 'queries.txt')
assert query_hash == 'f2440c27b9fa7596e902b5bc30a30130e10789564a75f661338742d40876d8ce'
queries = ROOT.joinpath('queries.txt').read_text().splitlines()
control = json.loads(ROOT.joinpath('r9-control/summary.json').read_text())
current = json.loads(ROOT.joinpath('r10-current/summary.json').read_text())
assert control['production_tree'] == TREE and control['scheduled']['valid_responses'] == 60
assert control['scheduled']['project_citations'] == 8 and current['scheduled']['project_citations'] == 6
assert current['production_tree'] == LIVE_TREE and current['decision'] == 'discard'
pool_path = INSTANCE / 'candidate-pool.json'
original_hash = digest(pool_path)
pool = json.loads(pool_path.read_text())
assert {entry['id'] for entry in pool['history']} == {f'r{i}' for i in range(11)}
write('candidate-pool-before.json', pool)
selected = next(p for p in pool['proposals'] if p['id'] == 'reference-cluster-without-r7')
assert not selected.get('measured', False)
original_proposal = copy.deepcopy(selected)
selected.update({'round': 11, 'change_id': 'r11-reference-cluster-without-r7', 'status': 'selected_preparing',
    'measured': False, 'original_proposal': original_proposal, 'base_commit': BASE,
    'parents': ['r2', 'r3', 'r4', 'r6', 'r8', 'r9'], 'files': ['index.html'],
    'modules': ['homepage-identity', 'method-reference', 'research-context', 'paper-authority', 'presentation'],
    'module_dependencies': ['R6: exact pre-R7 overview source', 'R8: retained cross-module reference routes', 'R9: retained static benchmark results'],
    'scope': 'Restore only section:overview from R6 on the R9 seed. Keep every other R9 byte unchanged.',
    'reuse_kind': 'Rebase the existing no-R7 reference-cluster proposal onto the stronger R9 seed, preserving R9 static evidence instead of resetting to the older R6 tree.',
    'hypothesis': 'Test the retained R8 reference cluster and R9 static evidence with the pre-R7 overview; do not infer a combination score from historical results.',
    'reason_selected': 'R10 did not beat R9. Resume from the best fully observed seed and test an already queued historical combination, rather than carry an unkept metadata edit forward automatically.',
    'alternatives_deferred': ['external-paper-link-audit', 'new visible-identity headline experiment', 'R10 shared identity recombination'],
    'interpretation': 'Unmeasured candidate; this fixed intervention is not a tuned module-deletion comparison or a causal ablation.',
    'retain_for_combinations': True})
policy = {'primary_metric': 'live_project_citation_rate', 'goal': 'maximize',
    'definition': '100 * frozen geo_eval site_cited cells / 60; bare project-domain occurrences count under the existing judge.',
    'engines': ['gpt-web', 'codex-search', 'tavily-search', 'exa-search'],
    'validity': 'All 60 frozen query-engine cells must return valid responses for automatic ranking.',
    'inner_metric': 'not computed and not used',
    'baseline': 'Best fully observed R9 seed: preserved 2026-10-16T13:09:24Z observation, 8/60 citations, composite 30.25; reused historical control, not new searches.',
    'current_production': 'R10 is still deployed and had 6/60, composite 28.0556; contextual only, not the R11 keep threshold.',
    'deployment': 'Require explicit R11 publication approval, all four resources differing from current R10 byte-verified, and real 60-cell observations before evaluating the candidate.',
    'history': 'Retain all discarded candidates and queued proposals; never add parent metrics to rank a combination.',
    'limitations': 'Historical single samples do not establish causal effects or exclude indexing lag. No automatic deployment or rollback.'}
pool.update({'current_round': 11, 'selected_candidate_id': selected['id'], 'policy': policy,
             'updated_at': dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')})
write('outer-only-policy.json', policy)
write('outer-measurements.json', {'measurements': [{'label': 'r9-best-reused-control', 'deployed_commit': BASE,
    'deployed_tree': TREE, 'measured_at': control['measured_at'], 'query_sha256': query_hash,
    'matrix': 'r9-control/search-matrix.csv', 'matrix_sha256': digest(ROOT / 'r9-control/search-matrix.csv'),
    'verification': 'Reused exact R9 deployed tree with preserved complete live evidence; R9 is selection seed, not current production.'}]})
write('production-context.json', {'production_commit': LIVE, 'production_tree': LIVE_TREE,
    'selection_seed_commit': BASE, 'selection_seed_tree': TREE, 'production_observation': current['scheduled'],
    'seed_observation': control['scheduled'], 'restore_overview_from': RESTORE,
    'production_unchanged': True, 'requires_separate_publication_approval': True})
config = {'site_url': 'https://eau-meta-agent.github.io/', 'paper_url': 'https://arxiv.org/abs/2610.16523',
    'repo_url': 'https://github.com/eau-meta-agent/eau-meta-agent.github.io',
    'platforms': {engine: .25 for engine in policy['engines']},
    'queries': [{'id': f'Q{i:02d}', 'text': q} for i, q in enumerate(queries, 1)],
    'interventions': [{'id': selected['change_id'], 'candidate_id': selected['change_id'],
        'nodes': ['section:overview', 'file:method.html', 'file:paper.html', 'file:research-context.html', 'section:results'],
        'source_url': 'https://eau-meta-agent.github.io/', 'link_state': 'present',
        'link_evidence_url': 'https://eau-meta-agent.github.io/', 'change_kind': 'node',
        'local_state': 'R9 retains the R7 overview alongside R8 reference links and static results.',
        'hypothesis': selected['hypothesis'], 'candidate_arms': [{'id': p['id'], 'status': p['status'], 'hypothesis': p['hypothesis']} for p in pool['proposals']]},
        {'id': 'external-paper-link-audit', 'nodes': ['external:paper-backlink'],
         'source_url': 'https://arxiv.org/abs/2610.16523', 'link_state': 'unknown', 'owner': 'paper author',
         'change_kind': 'edge', 'hypothesis': 'External paper edits require separate author authority; none is part of R11.'}]}
write('config.json', config)
engine_files = {'gpt-web': 'gpt-web-answers.jsonl', 'codex-search': 'codex-answers-complete.jsonl', 'tavily-search': 'tavily-answers.jsonl', 'exa-search': 'exa-answers.jsonl'}
answers = {engine: {r['query']: r for r in map(json.loads, ROOT.joinpath('r9-control', name).read_text().splitlines())} for engine, name in engine_files.items()}
write('r9-search-evidence.json', {'tool': 'R9 saved four-engine responses (not new R11 probes)',
    'result_scope': 'Displayed URLs from preserved answers; not top-ten ranks or predicted lift',
    'observations': [{'query_id': f'Q{i:02d}',
        'result_urls': list(dict.fromkeys(u.rstrip('.,;:!?*_') for engine in engine_files for u in URL_RE.findall(answers[engine][q]['text']))),
        'raw_file': 'r9-control/gpt-web-answers.jsonl',
        'raw_files': {engine: 'r9-control/' + name for engine, name in engine_files.items()}} for i, q in enumerate(queries, 1)]})
write('change.json', {'round': 11, 'change_id': selected['change_id'], 'pool_candidate_id': selected['id'],
    'state': 'preparing', 'files': ['index.html'], 'graph_nodes': ['section:overview'],
    'base_production_commit': BASE, 'base_production_tree': TREE, 'base_role': 'historical best seed, NOT current production',
    'current_production_commit': LIVE, 'current_production_tree': LIVE_TREE,
    'parents': selected['parents'], 'restore_overview_from': RESTORE, 'hypothesis': selected['hypothesis'],
    'selection': policy, 'knowledge_map_sha256': digest(INSTANCE / 'map.json'),
    'unchanged_vs_seed': ['R8 reference cluster', 'R9 static results', 'all other sections and files', 'scripts', 'styles', 'metadata', 'knowledge map', 'queries', 'judge', 'engine settings'],
    'excluded_unkept_delta': 'R10 shared scholarly identity is not in the R9 seed; its branch and observations remain preserved.',
    'deployment_plan': 'Do not blindly merge this R9-based candidate onto R10: that would retain R10 metadata. After explicit approval, use an isolated deploy branch based on current main, apply the saved production-to-candidate patch, verify exact candidate tree, then merge and publish. All four changed pages need served-byte proof.'})
cli('scan', '--no-interactive', name='wrapper-scan.txt')
cli('configure', '--part', 'index.html', '--metric', 'live_project_citation_rate', '--metric-goal', 'maximize',
    '--metric-command', f'python3 {ROOT / "outer_metric.py"}', '--mode', 'sequential', '--rounds', '1',
    '--metric-timeout', '120', '--no-interactive', name='wrapper-configure.txt')
run = json.loads(cli('run', '--part', 'index.html', '--no-interactive', '--json', name='wrapper-run.json'))
write('candidate-pool-selected.json', pool)
assert digest(pool_path) == original_hash, 'Concurrent ledger edits must be reconciled, not overwritten'
pool_path.write_text(json.dumps(pool, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({'run': run, 'seed': 'R9 best observed, 8/60', 'current_production': 'R10, unchanged',
                  'selected': selected['id'], 'inner_score': 'not computed'}, indent=2))
