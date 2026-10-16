"""Prepare the queued second-backbone static-evidence test after measured R13."""
import copy
import datetime as dt
import shutil
from common import *
from geo_eval.discovery import URL_RE

assert os.environ.get('SLURM_JOB_ID')
current_dir = INSTANCE / 'runs/round-13-static-component-reference/r13-live'
current = json.loads(current_dir.joinpath('summary.json').read_text())
current_audit = json.loads(current_dir.joinpath('audit.json').read_text())
assert current_audit['passed'] and current['scheduled']['valid_responses'] == 60
assert current['decision'] == 'discard' and current['scheduled']['project_citations'] == 7
base = '52dee0ba78885b9a3028760ba8d9cfc749a6c2e7'
base_tree = '5ebd5d1c28e00690d58caafa0edfe066ae5307d7'
control_dir = INSTANCE / 'runs/round-9-static-benchmark-evidence/r9-live'
control = json.loads(control_dir.joinpath('summary.json').read_text())
assert control['scheduled']['valid_responses'] == 60 and control['scheduled']['project_citations'] == 8
assert control['production_tree'] == base_tree
assert git(SITE, 'rev-parse', 'HEAD') == base and git(SITE, 'rev-parse', 'HEAD^{tree}') == base_tree
assert not git(SITE, 'status', '--porcelain') and not git(PRODUCTION, 'status', '--porcelain')
assert git(PRODUCTION, 'rev-parse', 'HEAD') == current['production_merge_commit'] == 'c6fa063d86be9e1861b0d79c6d2f7e2c27e3c1aa'
assert git(PRODUCTION, 'rev-parse', 'HEAD^{tree}') == current['production_tree']
assert ROOT.joinpath('r13-production-index.html').read_bytes() == PRODUCTION.joinpath('index.html').read_bytes()
pool_path = INSTANCE / 'candidate-pool.json'
original_hash = digest(pool_path)
pool = json.loads(pool_path.read_text())
assert pool['current_round'] == 13 and {h['id'] for h in pool['history']} == {f'r{i}' for i in range(14)}
assert len(pool['proposals']) == 8 and all(h['retain_for_combinations'] for h in pool['history'])
selected = next(p for p in pool['proposals'] if p['id'] == SELECTED)
assert selected['status'] == 'queued_unmeasured' and selected['measured'] is False
write('candidate-pool-before.json', pool)
original_proposal = copy.deepcopy(selected)
selected.update({'original_proposal': original_proposal, 'round': 14, 'change_id': CHANGE_ID,
    'status': 'selected_preparing', 'base_commit': base, 'files': ['index.html'],
    'reason_selected': 'R13 preserved four explicit homepage URL cells and no support-page URL cells, but did not beat R9. R9 already exposes the default Qwen3 result data. The existing second-backbone rows remain only in script.js until the model switch is used; test a separately labelled static reference for those exact rows on the best measured seed.',
    'scope': 'Insert one default-open, separately captioned Qwen2.5-7B-Instruct result reference into the existing results section; preserve every original byte, including the default charts/table and model switch. Copy all nine method rows and 36 values exactly from existing JS.',
    'module_dependencies': ['index.html#results, existing main charts and comparison table', 'script.js results.qwen25 values and label, unchanged', 'styles.css existing result-table-details/table-scroll table styles, unchanged', 'R7 overview, R8 routes and R9 static default evidence, retained'],
    'alternatives_deferred': ['static-component-reference retained for combinations despite R13 discard', 'homepage-descriptive-h1 retained despite R12 discard', 'external-paper-link-audit requires separate author authority'],
    'interpretation': 'Unmeasured local hypothesis, not predicted lift; historical parent scores and a returned source URL do not certify a combination.'})
ROOT.joinpath('control').mkdir(exist_ok=True)
for name in ['summary.json', 'search-matrix.csv', 'search-map.json']:
    shutil.copy2(control_dir / name, ROOT / 'control' / name)
for name in ['queries.txt', 'search-map.json', 'outer_metric.py']:
    shutil.copy2(INSTANCE / 'runs/round-13-static-component-reference' / name, ROOT / name)
assert digest(ROOT / 'queries.txt') == 'f2440c27b9fa7596e902b5bc30a30130e10789564a75f661338742d40876d8ce'
assert digest(ROOT / 'control/search-matrix.csv') == 'deebdf85fe8751eb8d7e53f9256a539fe50101ea3403550df06c7ce05a55b577'
ROOT.joinpath('r13-evidence').mkdir(exist_ok=True)
engine_files = {'gpt-web': 'gpt-web-answers.jsonl', 'codex-search': 'codex-answers-complete.jsonl',
                'tavily-search': 'tavily-answers.jsonl', 'exa-search': 'exa-answers.jsonl'}
for name in ['summary.json', *engine_files.values()]:
    shutil.copy2(current_dir / name, ROOT / 'r13-evidence' / name)
queries = ROOT.joinpath('queries.txt').read_text().splitlines()
answers = {engine: {r['query']: r for r in map(json.loads, ROOT.joinpath('r13-evidence', name).read_text().splitlines())}
           for engine, name in engine_files.items()}
write('r13-search-evidence.json', {'tool': 'Preserved actual R13 four-engine responses; no new R14 searches',
    'result_scope': 'Source URLs displayed in those saved responses; not a top-ten rank or predicted intervention lift',
    'observations': [{'query_id': f'Q{i:02d}', 'result_urls': list(dict.fromkeys(
        u.rstrip('.,;:!?*_') for engine in engine_files for u in URL_RE.findall(answers[engine][query]['text']))),
        'raw_file': 'r13-evidence/gpt-web-answers.jsonl',
        'raw_files': {engine: 'r13-evidence/' + name for engine, name in engine_files.items()}}
        for i, query in enumerate(queries, 1)]})
policy = {'primary_metric': 'live_project_citation_rate', 'goal': 'maximize',
    'definition': '100 * frozen geo_eval site_cited cells / 60, including bare project-domain occurrences under the existing judge',
    'engines': list(engine_files), 'validity': 'All 60 frozen query-engine cells must be valid; otherwise remain unranked',
    'inner_metric': 'not computed and not used',
    'baseline': 'Best fully observed R9: 8/60, composite 30.25; reused historical control, not new or simultaneous collection',
    'current_production': 'R13 remains deployed: 7/60, composite 30.13889, discard; do not lower the selection threshold to current production',
    'deployment': 'Separate explicit R14 publication approval required; exact candidate tree and served bytes before/after all 60 real probes must be verified',
    'history': 'Retain all discarded and kept candidates plus original proposals for combinations; never add parent scores',
    'limitations': 'Immediate single samples and historical controls do not establish causality or exclude indexing lag; no automatic rollback or follow-up'}
write('outer-only-policy.json', policy)
pool.update({'current_round': 14, 'selected_candidate_id': SELECTED, 'policy': policy,
             'updated_at': dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')})
write('production-context.json', {'production_commit': current['production_merge_commit'],
    'production_tree': current['production_tree'], 'production_observation': current['scheduled'],
    'selection_seed_round': 9, 'selection_seed_commit': base, 'selection_seed_tree': base_tree,
    'seed_observation': control['scheduled'], 'seed_measurement_dir': str(control_dir),
    'production_unchanged': True, 'requires_separate_publication_approval': True})
write('outer-measurements.json', {'measurements': [{'label': 'r9-best-reused-control',
    'deployed_commit': control['production_merge_commit'], 'deployed_tree': base_tree,
    'measured_at': control['measured_at'], 'query_sha256': digest(ROOT / 'queries.txt'),
    'matrix': 'control/search-matrix.csv', 'matrix_sha256': digest(ROOT / 'control/search-matrix.csv'),
    'verification': 'Exact preserved best fully measured tree; historical control, not new search collection'}]})
write('module-review.json', {'basis': 'Complete actual R13 and preserved R9-R12 outer evidence plus existing public site source; no new R14 probes',
    'latest_observation': {'round': 13, 'citations': 7, 'explicit_project_url_cells': 4,
        'explicit_support_page_url_cells': 0, 'gained_vs_r9': current['citation_transitions']['gained'],
        'lost_vs_r9': current['citation_transitions']['lost'], 'decision': 'discard'},
    'reviews': [
        {'module': 'homepage-identity', 'action': 'Retain R9 identity/overview; preserve unkept R12 H1 in history'},
        {'module': 'presentation', 'action': 'Select second-backbone static result reference using existing JS data and table styling; no model-switch code edits'},
        {'module': 'reference-pages', 'action': 'Retain R8 reference cluster; no explicit support-page URLs in R13, not evidence that another edge will lift citations'},
        {'module': 'method-reference', 'action': 'Retain R9 method page; preserve R13 static component variant as a later combination parent, not silently inherited'},
        {'module': 'research-context', 'action': 'Retain factual evaluation boundaries and caveats'},
        {'module': 'paper-authority', 'action': 'Retain seed metadata and numerical scope; no fabricated Qwen2.5 tau2 numbers or new gains'},
        {'module': 'machine-readable-summary', 'action': 'Retain llms.txt unchanged'},
        {'module': 'crawler-routing', 'action': 'Retain robots/sitemap; served bytes do not prove recrawling or indexing'},
        {'module': 'repository-authority', 'action': 'Retain existing R5 README bridge; no external repository mutation'},
        {'module': 'external-paper-entry', 'action': 'Link state stays unknown; defer any external author-owned edit pending separate authority'}]})
config = {'site_url': 'https://eau-meta-agent.github.io/', 'paper_url': 'https://arxiv.org/abs/2610.16523',
    'repo_url': 'https://github.com/eau-meta-agent/eau-meta-agent.github.io',
    'platforms': {engine: .25 for engine in engine_files},
    'queries': [{'id': f'Q{i:02d}', 'text': query} for i, query in enumerate(queries, 1)],
    'interventions': [{'id': CHANGE_ID, 'candidate_id': CHANGE_ID,
        'nodes': ['file:index.html', 'section:results', 'file:script.js', 'file:styles.css'],
        'source_url': 'https://eau-meta-agent.github.io/', 'link_state': 'present',
        'link_evidence_url': 'https://eau-meta-agent.github.io/', 'change_kind': 'node',
        'local_state': 'Default Qwen3 rows are static; second-backbone Qwen2.5 rows require the JS model switch',
        'hypothesis': selected['hypothesis'],
        'candidate_arms': [{'id': p['id'], 'status': p['status'], 'hypothesis': p['hypothesis']} for p in pool['proposals']]},
        {'id': 'external-paper-link-audit', 'nodes': ['external:paper-backlink'],
         'source_url': 'https://arxiv.org/abs/2610.16523', 'link_state': 'unknown', 'owner': 'paper author',
         'change_kind': 'edge', 'hypothesis': 'External paper edits require separate authority and are outside R14'}]}
write('config.json', config)
write('change.json', {'round': 14, 'change_id': CHANGE_ID, 'pool_candidate_id': SELECTED,
    'state': 'preparing', 'files': ['index.html'], 'graph_nodes': ['file:index.html', 'section:results'],
    'selection_seed_round': 9, 'selection_seed_commit': base, 'selection_seed_tree': base_tree,
    'current_production_commit': current['production_merge_commit'], 'current_production_tree': current['production_tree'],
    'parents': selected['parents'], 'hypothesis': selected['hypothesis'], 'selection': policy,
    'knowledge_map_sha256': digest(INSTANCE / 'map.json'),
    'unchanged_vs_seed': ['every original index.html byte except one insertion', 'all other named sections',
        'existing main result charts, table, model-switch markup and noscript fallback', 'interactive component explorer',
        'scripts', 'styles', 'metadata', 'all original result values', 'knowledge map', 'queries', 'judge', 'engine settings'],
    'excluded_unkept_deltas': ['R10 shared scholarly identity', 'R11 overview restoration', 'R12 descriptive H1', 'R13 static component reference'],
    'deployment_plan': 'Require separate explicit R14 publication approval. Apply the exact candidate index.html in an isolated deploy branch based on then-current main and verify the complete tree. Relative to R13, index.html adds the second-backbone table and removes the unkept R13 component block. A blind merge would retain the wrong tree. Reconcile any teammate changes before proceeding.'})
cli('scan', '--no-interactive', name='wrapper-scan.txt')
cli('configure', '--part', 'index.html', '--metric', 'live_project_citation_rate', '--metric-goal', 'maximize',
    '--metric-command', f'python3 {ROOT / "outer_metric.py"}', '--mode', 'sequential', '--rounds', '1',
    '--metric-timeout', '120', '--no-interactive', name='wrapper-configure.txt')
run = json.loads(cli('run', '--part', 'index.html', '--no-interactive', '--json', name='wrapper-run.json'))
write('candidate-pool-selected.json', pool)
assert digest(pool_path) == original_hash, 'Concurrent ledger changes require reconciliation'
pool_path.write_text(json.dumps(pool, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({'run': run, 'selected': SELECTED, 'selection_seed_round': 9,
    'control_citations': 8, 'current_production': 'R13 unchanged, 7/60', 'inner_score': 'not computed'}, indent=2))
