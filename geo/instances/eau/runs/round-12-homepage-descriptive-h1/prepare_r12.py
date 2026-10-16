"""Refresh the candidate pool and select a visible identity heading on the R9 seed."""
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
SITE = Path('/scratch/henrycai/eau-r12-20261016')
PRODUCTION = Path('/project/aip-xiye17/henrycai/eau-meta-agent.github.io')
RUNNER = WRAPPER / 'skills/autoresearch-wrapper-run/run.sh'
BASE = '52dee0ba78885b9a3028760ba8d9cfc749a6c2e7'
TREE = '5ebd5d1c28e00690d58caafa0edfe066ae5307d7'
LIVE = 'c744ba125108d003ea61e8b89807e274ffaa6e4e'
LIVE_TREE = 'ccf91bf07379aae81ec4ba3c698803d0bd69368c'


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
assert ROOT.joinpath('r11-production-index.html').read_bytes() == PRODUCTION.joinpath('index.html').read_bytes()
query_hash = digest(ROOT / 'queries.txt')
assert query_hash == 'f2440c27b9fa7596e902b5bc30a30130e10789564a75f661338742d40876d8ce'
queries = ROOT.joinpath('queries.txt').read_text().splitlines()
control = json.loads(ROOT.joinpath('r9-control/summary.json').read_text())
current = json.loads(ROOT.joinpath('r11-evidence/summary.json').read_text())
assert control['production_tree'] == TREE and control['scheduled']['valid_responses'] == 60
assert control['scheduled']['project_citations'] == 8 and current['scheduled']['project_citations'] == 7
assert current['production_tree'] == LIVE_TREE and current['decision'] == 'discard'
pool_path = INSTANCE / 'candidate-pool.json'
original_hash = digest(pool_path)
pool = json.loads(pool_path.read_text())
assert {entry['id'] for entry in pool['history']} == {f'r{i}' for i in range(12)}
write('candidate-pool-before.json', pool)
new_proposals = [
    {'id': 'homepage-descriptive-h1', 'status': 'selected_preparing', 'measured': False,
     'parents': ['r1', 'r6', 'r7', 'r8', 'r9'], 'modules': ['homepage-identity', 'presentation', 'paper-authority'],
     'hypothesis': 'Put the existing EAU name and co-evolution topic in the visible primary heading; test outer discovery without changing facts or metadata.'},
    {'id': 'static-second-backbone-evidence', 'status': 'queued_unmeasured', 'measured': False,
     'parents': ['r4', 'r9'], 'modules': ['homepage-identity', 'presentation', 'paper-authority'],
     'hypothesis': 'Expose the existing Qwen2.5-7B-Instruct result rows in separately labelled static HTML while preserving the default model and switch; no mixed-backbone or invented results.'},
    {'id': 'static-component-reference', 'status': 'queued_unmeasured', 'measured': False,
     'parents': ['r2', 'r7', 'r9'], 'modules': ['homepage-identity', 'method-reference', 'presentation'],
     'hypothesis': 'Expose the existing environment and agent tab descriptions in accessible static HTML while preserving the interactive explorer and avoiding duplicate padding.'},
]
assert not {p['id'] for p in pool['proposals']} & {p['id'] for p in new_proposals}
for proposal in new_proposals:
    proposal['retain_for_combinations'] = True
pool['proposals'].extend(new_proposals)
selected = next(p for p in pool['proposals'] if p['id'] == 'homepage-descriptive-h1')
selected.update({'round': 12, 'change_id': 'r12-homepage-descriptive-h1', 'base_commit': BASE, 'files': ['index.html'],
    'module_dependencies': ['index.html: existing name, subtitle and hero-title ARIA target', 'styles.css: unchanged two-line hero typography', 'R7/R8/R9: retain overview, references and static evidence'],
    'scope': 'Replace only the existing hero h1 contents with EAU: / Co-evolution.; keep the id, two-line structure and emphasis markup.',
    'reason_selected': 'R11 returned four explicit homepage URLs but no support-page URLs. The homepage h1 is still Learning to evolve, together., while EAU and the full title are outside that h1. Test this small visible identity change on the already observed entry page.',
    'alternatives_deferred': ['static-second-backbone-evidence', 'static-component-reference', 'external-paper-link-audit'],
    'interpretation': 'Unmeasured local hypothesis, not predicted citation lift; broader page/module review is recorded separately.'})
write('new-proposals.json', new_proposals)
write('module-review.json', {'basis': 'R9/R10/R11 frozen outer records and local source inspection; no new R12 probes',
    'reviews': [
        {'module': 'homepage-identity', 'observation': 'Poetic h1 omits EAU; unchanged subtitle supplies full title.', 'action': 'select descriptive-h1 test'},
        {'module': 'presentation', 'observation': 'Default benchmark rows are static; second backbone and non-default tab descriptions remain in JS.', 'action': 'queue two separate unmeasured candidates'},
        {'module': 'method-reference', 'observation': 'Existing factual method page and R8 routes remain; no explicit support-page URLs in R11.', 'action': 'retain; do not predict lift from more edges'},
        {'module': 'research-context', 'observation': 'Existing scope and evaluation boundaries remain.', 'action': 'retain'},
        {'module': 'paper-authority', 'observation': 'Existing paper metadata and facts remain; R10 shared-ID test did not beat R9.', 'action': 'retain R9 metadata and R10 historical candidate'},
        {'module': 'machine-readable-summary', 'observation': 'llms.txt already contains identity and local reference routes.', 'action': 'retain'},
        {'module': 'crawler-routing', 'observation': 'robots allows crawling and sitemap lists current local pages.', 'action': 'retain; no claim that crawling or indexing occurred'},
        {'module': 'repository-authority', 'observation': 'R5 README bridge already exists.', 'action': 'retain'},
        {'module': 'external-paper-entry', 'observation': 'External backlink state remains unknown.', 'action': 'defer any edit pending separate author authority'}]})
policy = {'primary_metric': 'live_project_citation_rate', 'goal': 'maximize',
    'definition': '100 * frozen geo_eval site_cited cells / 60; bare project-domain occurrences count under the existing judge.',
    'engines': ['gpt-web', 'codex-search', 'tavily-search', 'exa-search'],
    'validity': 'All 60 frozen query-engine cells must return valid responses for automatic ranking.',
    'inner_metric': 'not computed and not used',
    'baseline': 'Best fully observed R9 seed: preserved 2026-10-16T13:09:24Z observation, 8/60 citations, composite 30.25; reused historical control, not new searches.',
    'current_production': 'R11 is still deployed and had 7/60, composite 28.9722; contextual only, not the R12 keep threshold.',
    'deployment': 'Require explicit R12 publication approval, exact candidate tree and served homepage bytes verified, and real 60-cell observations before evaluating the candidate.',
    'history': 'Retain all discarded candidates and queued proposals; never add parent metrics to rank a combination.',
    'limitations': 'Historical single samples do not establish causal effects or exclude indexing lag. No automatic deployment or rollback.'}
pool.update({'current_round': 12, 'selected_candidate_id': selected['id'], 'policy': policy,
             'updated_at': dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')})
write('outer-only-policy.json', policy)
write('outer-measurements.json', {'measurements': [{'label': 'r9-best-reused-control', 'deployed_commit': BASE,
    'deployed_tree': TREE, 'measured_at': control['measured_at'], 'query_sha256': query_hash,
    'matrix': 'r9-control/search-matrix.csv', 'matrix_sha256': digest(ROOT / 'r9-control/search-matrix.csv'),
    'verification': 'Reused exact R9 deployed tree with preserved complete live evidence; R9 is selection seed, not current production.'}]})
write('production-context.json', {'production_commit': LIVE, 'production_tree': LIVE_TREE,
    'selection_seed_commit': BASE, 'selection_seed_tree': TREE, 'production_observation': current['scheduled'],
    'seed_observation': control['scheduled'],
    'production_unchanged': True, 'requires_separate_publication_approval': True})
config = {'site_url': 'https://eau-meta-agent.github.io/', 'paper_url': 'https://arxiv.org/abs/2610.16523',
    'repo_url': 'https://github.com/eau-meta-agent/eau-meta-agent.github.io',
    'platforms': {engine: .25 for engine in policy['engines']},
    'queries': [{'id': f'Q{i:02d}', 'text': q} for i, q in enumerate(queries, 1)],
    'interventions': [{'id': selected['change_id'], 'candidate_id': selected['change_id'],
        'nodes': ['file:index.html', 'file:styles.css', 'section:overview', 'section:results'],
        'source_url': 'https://eau-meta-agent.github.io/', 'link_state': 'present',
        'link_evidence_url': 'https://eau-meta-agent.github.io/', 'change_kind': 'node',
        'local_state': 'Homepage h1 is a slogan without EAU, while the unchanged adjacent subtitle provides the full research title.',
        'hypothesis': selected['hypothesis'], 'candidate_arms': [{'id': p['id'], 'status': p['status'], 'hypothesis': p['hypothesis']} for p in pool['proposals']]},
        {'id': 'external-paper-link-audit', 'nodes': ['external:paper-backlink'],
         'source_url': 'https://arxiv.org/abs/2610.16523', 'link_state': 'unknown', 'owner': 'paper author',
         'change_kind': 'edge', 'hypothesis': 'External paper edits require separate author authority; none is part of R12.'}]}
write('config.json', config)
engine_files = {'gpt-web': 'gpt-web-answers.jsonl', 'codex-search': 'codex-answers-complete.jsonl', 'tavily-search': 'tavily-answers.jsonl', 'exa-search': 'exa-answers.jsonl'}
answers = {engine: {r['query']: r for r in map(json.loads, ROOT.joinpath('r11-evidence', name).read_text().splitlines())} for engine, name in engine_files.items()}
write('r11-search-evidence.json', {'tool': 'R11 saved four-engine responses (not new R12 probes)',
    'result_scope': 'Displayed URLs from preserved answers; not top-ten ranks or predicted lift',
    'observations': [{'query_id': f'Q{i:02d}',
        'result_urls': list(dict.fromkeys(u.rstrip('.,;:!?*_') for engine in engine_files for u in URL_RE.findall(answers[engine][q]['text']))),
        'raw_file': 'r11-evidence/gpt-web-answers.jsonl',
        'raw_files': {engine: 'r11-evidence/' + name for engine, name in engine_files.items()}} for i, q in enumerate(queries, 1)]})
write('change.json', {'round': 12, 'change_id': selected['change_id'], 'pool_candidate_id': selected['id'],
    'state': 'preparing', 'files': ['index.html'], 'graph_nodes': ['file:index.html'],
    'base_production_commit': BASE, 'base_production_tree': TREE, 'base_role': 'historical best seed, NOT current production',
    'current_production_commit': LIVE, 'current_production_tree': LIVE_TREE,
    'parents': selected['parents'], 'hypothesis': selected['hypothesis'],
    'selection': policy, 'knowledge_map_sha256': digest(INSTANCE / 'map.json'),
    'unchanged_vs_seed': ['R7 overview', 'R8 reference cluster', 'R9 static results', 'all other HTML bytes and files', 'scripts', 'styles', 'metadata', 'knowledge map', 'queries', 'judge', 'engine settings'],
    'excluded_unkept_deltas': ['R10 shared scholarly identity', 'R11 overview restoration'],
    'deployment_plan': 'Do not blindly merge this R9-based candidate into R11: that would retain the unkept R11 overview. After explicit approval, use an isolated deploy branch based on current main, apply exact candidate content for index.html, verify the entire candidate tree, then merge and publish. Relative to production, index.html contains both the intended h1 test and the restoration of the R9 overview.'})
cli('scan', '--no-interactive', name='wrapper-scan.txt')
cli('configure', '--part', 'index.html', '--metric', 'live_project_citation_rate', '--metric-goal', 'maximize',
    '--metric-command', f'python3 {ROOT / "outer_metric.py"}', '--mode', 'sequential', '--rounds', '1',
    '--metric-timeout', '120', '--no-interactive', name='wrapper-configure.txt')
run = json.loads(cli('run', '--part', 'index.html', '--no-interactive', '--json', name='wrapper-run.json'))
write('candidate-pool-selected.json', pool)
assert digest(pool_path) == original_hash, 'Concurrent ledger edits must be reconciled, not overwritten'
pool_path.write_text(json.dumps(pool, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({'run': run, 'seed': 'R9 best observed, 8/60', 'current_production': 'R11, unchanged',
                  'selected': selected['id'], 'inner_score': 'not computed'}, indent=2))
