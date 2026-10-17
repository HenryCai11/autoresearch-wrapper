"""Prepare a factual heading intervention, retaining every old proposal and observation."""
import copy
import datetime as dt
import shutil
from common import *
from geo_eval.discovery import URL_RE

assert os.environ.get('SLURM_JOB_ID')
assert not ROOT.joinpath('wrapper-run.json').exists(), 'Do not start a second R16 run'
previous = INSTANCE / 'runs/round-15-static-entry-combination'
live = previous / 'r15-live'
current = json.loads(live.joinpath('summary.json').read_text())
assert json.loads(live.joinpath('audit.json').read_text())['passed']
assert current['scheduled']['valid_responses'] == 60 and current['scheduled']['project_citations'] == 6 and current['decision'] == 'discard'
base = '52dee0ba78885b9a3028760ba8d9cfc749a6c2e7'
tree = '5ebd5d1c28e00690d58caafa0edfe066ae5307d7'
assert git(SITE, 'rev-parse', 'HEAD') == base and git(SITE, 'rev-parse', 'HEAD^{tree}') == tree
assert not git(SITE, 'status', '--porcelain') and not git(PRODUCTION, 'status', '--porcelain')
assert git(PRODUCTION, 'rev-parse', 'HEAD') == current['production_merge_commit'] == '596ccda6c33a4bb2ea9cac3daa7d489e856f264d'
assert git(PRODUCTION, 'rev-parse', 'HEAD^{tree}') == current['production_tree']
assert ROOT.joinpath('r15-production-index.html').read_bytes() == PRODUCTION.joinpath('index.html').read_bytes()
pool_path = INSTANCE / 'candidate-pool.json'
old_hash = digest(pool_path)
pool = json.loads(pool_path.read_text())
assert pool['current_round'] == 15 and {h['id'] for h in pool['history']} == {f'r{i}' for i in range(16)}
assert len(pool['proposals']) == 9 and SELECTED not in {p['id'] for p in pool['proposals']}
write('candidate-pool-before.json', pool)
source = SITE.joinpath('index.html').read_text()
operations = [
    {'op': 'replace_text', 'node': 'file:index.html',
     'before': '<h2 id="framework-title">A feedback loop.<br><em>With room to change.</em></h2>',
     'after': '<h2 id="framework-title">How EAU adapts<br><em>the training system.</em></h2>'},
    {'op': 'replace_text', 'node': 'file:index.html',
     'before': '<h2 id="results-title">Better interactions.<br><em>Stronger agents.</em></h2>',
     'after': '<h2 id="results-title">EAU results on<br><em>UserGym and ColBench.</em></h2>'},
]
assert all(source.count(op['before']) == 1 and op['after'] not in source for op in operations)
write('operations.json', {'operations': operations})
facts = json.loads(INSTANCE.joinpath('map.json').read_text())
by_node = {node['id']: node for node in facts['nodes']}
assert 'training system' in by_node['adaptive-training-system']['fact']
assert all(term in by_node['benchmarks']['fact'] for term in ['UserGym', 'ColBench'])
write('heading-source.json', {'seed_commit': base, 'operation_count': 2, 'new_facts': False,
    'headings': [
        {'id': 'framework-title', 'before': operations[0]['before'], 'after': operations[0]['after'],
         'map_node': 'adaptive-training-system', 'fact': by_node['adaptive-training-system']['fact'],
         'existing_visible_source': 'research-context.html#scope',
         'existing_source_excerpt': 'It treats the training system as editable, using rollout evidence to select and validate interventions while evaluation remains fixed.'},
        {'id': 'results-title', 'before': operations[1]['before'], 'after': operations[1]['after'],
         'map_node': 'benchmarks', 'fact': by_node['benchmarks']['fact'],
         'existing_visible_source': 'index.html#results',
         'existing_source_excerpt': 'Evaluated on UserGym, ColBench, and τ²-bench.'}],
    'scope': 'Only two existing visible H2 texts; preserve IDs, br/em structure, paragraphs, tables, metadata and assets.',
    'score_policy': 'Unmeasured new intervention; R15 source presence and historical scores do not predict lift.'})
selected = {'id': SELECTED, 'status': 'selected_preparing', 'measured': False, 'round': 16,
    'change_id': CHANGE_ID, 'parents': ['r9'], 'retain_for_combinations': True,
    'modules': ['homepage-identity', 'presentation'], 'files': ['index.html'], 'base_commit': base,
    'hypothesis': 'Replace framework/results creative H2 labels with factual method/benchmark headings to test passage context on the observed homepage entry surface.',
    'reason_selected': 'R15 has 6/60 citations, all exact-tier, with 0 fuzzy/broad and no support-page URL cells. Test two existing homepage headings without content expansion or inheriting the discarded R15 bundle; source visibility is not estimated lift.',
    'scope': 'Two H2 text replacements only; no new facts, numbers, claims, links, styles, scripts, schema or padding.',
    'module_dependencies': ['index.html framework-title and results-title', 'existing styles.css heading layout, unchanged',
        'existing script.js and model-switch targets, unchanged', 'R7 overview, R8 routes and R9 static data, retained'],
    'interpretation': 'Unmeasured whole-candidate hypothesis; immediate historical observations cannot isolate module effects or rule out indexing lag.'}
pool['proposals'].append(selected)
write('new-proposals.json', [selected])
control = INSTANCE / 'runs/round-9-static-benchmark-evidence/r9-live'
ROOT.joinpath('control').mkdir(exist_ok=True)
for name in ['summary.json', 'search-matrix.csv', 'search-map.json']:
    shutil.copy2(control / name, ROOT / 'control' / name)
for name in ['outer_metric.py', 'queries.txt', 'search-map.json']:
    shutil.copy2(previous / name, ROOT / name)
assert digest(ROOT / 'queries.txt') == 'f2440c27b9fa7596e902b5bc30a30130e10789564a75f661338742d40876d8ce'
assert digest(ROOT / 'control/search-matrix.csv') == 'deebdf85fe8751eb8d7e53f9256a539fe50101ea3403550df06c7ce05a55b577'
control_summary = json.loads(control.joinpath('summary.json').read_text())
assert control_summary['scheduled']['valid_responses'] == 60 and control_summary['scheduled']['project_citations'] == 8
registry = json.loads(previous.joinpath('outer-measurements.json').read_text())
registry['measurements'] = [r for r in registry['measurements'] if r['label'] == 'r9-best-reused-control']
assert len(registry['measurements']) == 1
registry['measurements'][0]['matrix'] = 'control/search-matrix.csv'
write('outer-measurements.json', registry)
write('production-context.json', {'production_commit': current['production_merge_commit'], 'production_tree': current['production_tree'],
    'production_observation': current['scheduled'], 'selection_seed_round': 9, 'selection_seed_commit': base,
    'selection_seed_tree': tree, 'seed_observation': control_summary['scheduled'],
    'production_unchanged': True, 'requires_separate_publication_approval': True})
policy = copy.deepcopy(pool['policy'])
policy.update({'current_production': 'R15 unchanged, 6/60, composite 29.75, discard; not the selection threshold',
    'baseline': 'Best complete R9, 8/60, composite 30.25; reused historical control, not fresh/simultaneous',
    'deployment': 'Separate explicit R16 approval required, exact candidate tree and served bytes verified before/after all 60 real requests',
    'history': 'All nine old proposals and 16 old history entries are unchanged; one new heading proposal is separate and unmeasured; do not add parent scores'})
write('outer-only-policy.json', policy)
engine_files = {'gpt-web': 'gpt-web-answers.jsonl', 'codex-search': 'codex-answers-complete.jsonl',
                'tavily-search': 'tavily-answers.jsonl', 'exa-search': 'exa-answers.jsonl'}
ROOT.joinpath('r15-evidence').mkdir(exist_ok=True)
for name in ['summary.json', *engine_files.values()]:
    shutil.copy2(live / name, ROOT / 'r15-evidence' / name)
queries = ROOT.joinpath('queries.txt').read_text().splitlines()
answers = {engine: {r['query']: r for r in map(json.loads, ROOT.joinpath('r15-evidence', name).read_text().splitlines())} for engine,name in engine_files.items()}
assert all(len(rows) == 15 and set(rows) == set(queries) and all(row['status'] == 'ok' for row in rows.values()) for rows in answers.values())
write('r15-search-evidence.json', {'tool': 'Saved actual R15 four-engine answers; not new R16 probes',
    'result_scope': 'Displayed source URLs only, not top-ten ranks or predicted intervention lift',
    'observations': [{'query_id': f'Q{i:02d}', 'result_urls': list(dict.fromkeys(u.rstrip('.,;:!?*_') for engine in engine_files for u in URL_RE.findall(answers[engine][query]['text']))),
        'raw_file': 'r15-evidence/gpt-web-answers.jsonl',
        'raw_files': {engine: 'r15-evidence/' + name for engine,name in engine_files.items()}} for i,query in enumerate(queries, 1)]})
actions = {'homepage-identity': 'Test two descriptive H2 labels; retain original R9 H1, subtitle and overview',
    'presentation': 'Preserve h2 IDs, br/em markup and all styles; no browser/visual validation claimed',
    'method-reference': 'Reuse supported training-system concept in heading; method page and component descriptions unchanged',
    'research-context': 'Fact source for editable training system; context page unchanged',
    'paper-authority': 'Retain all metadata and evidence boundaries; no new claims or scholarly-entity changes',
    'machine-readable-summary': 'Retain llms.txt; R15 has no support-page URL retrieval evidence',
    'repository-authority': 'Retain existing README bridge; no external repository mutation',
    'crawler-routing': 'Retain robots/sitemap; served content does not prove indexing',
    'reference-pages': 'Retain R8 routes and all reference pages; no extra link or content expansion',
    'external-paper-entry': 'Unknown backlink state; edits still need separate author authority'}
assert set(actions) == {m['id'] for m in pool['modules']}
write('module-review.json', {'basis': 'Actual completed R15 60-cell measurement and preserved R9 control; no new R16 searches',
    'latest_observation': {'round': 15, 'citations': 6, 'explicit_project_url_cells': 4,
        'explicit_support_page_url_cells': 0, 'fuzzy_citations': 0, 'broad_citations': 0, 'decision': 'discard'},
    'reviews': [{'module': key, 'action': value} for key,value in actions.items()],
    'alternatives_retained': [
        {'ids': ['homepage-descriptive-h1', 'static-component-reference', 'static-second-backbone-evidence', 'static-entry-combination'],
         'decision': 'Retain exact operations and observations for future combinations; do not silently inherit into R16'},
        {'ids': ['shared-scholarly-entity', 'reference-cluster-without-r7', 'r8-reference-cluster'],
         'decision': 'Retain prior candidates without claiming causal module effects'},
        {'ids': ['external-paper-link-audit'], 'decision': 'Unmeasured and authority-gated, not silently performed'}],
    'selection_limit': 'Source visibility and immediate historical samples do not predict heading lift or isolate module effects.'})
config = json.loads(previous.joinpath('config.json').read_text())
config['interventions'][0] = {'id': CHANGE_ID, 'candidate_id': CHANGE_ID,
    'nodes': ['file:index.html', 'section:framework', 'section:results', 'file:script.js', 'file:styles.css'],
    'source_url': 'https://eau-meta-agent.github.io/', 'link_state': 'present', 'link_evidence_url': 'https://eau-meta-agent.github.io/',
    'change_kind': 'node', 'local_state': 'On R9, framework/results H2 use creative labels instead of method and benchmark names',
    'hypothesis': selected['hypothesis'], 'candidate_arms': [{'id': p['id'], 'status': p['status'], 'hypothesis': p['hypothesis']} for p in pool['proposals']]}
config['interventions'][1]['hypothesis'] = 'External paper edits require separate authority and are outside R16'
write('config.json', config)
write('change.json', {'round': 16, 'change_id': CHANGE_ID, 'pool_candidate_id': SELECTED, 'state': 'preparing',
    'files': ['index.html'], 'graph_nodes': ['file:index.html', 'section:framework', 'section:results'],
    'selection_seed_round': 9, 'selection_seed_commit': base, 'selection_seed_tree': tree,
    'current_production_commit': current['production_merge_commit'], 'current_production_tree': current['production_tree'],
    'parents': selected['parents'], 'hypothesis': selected['hypothesis'], 'selection': policy,
    'knowledge_map_sha256': digest(INSTANCE / 'map.json'),
    'unchanged_vs_seed': ['all bytes except two existing H2 labels', 'hero/H1 and R7 overview', 'R8 links', 'R9 static result data',
        'other pages', 'paragraphs', 'links', 'tables', 'scripts', 'styles', 'metadata', 'map', 'queries', 'judge', 'engine settings'],
    'deployment_plan': 'Require separate R16 approval. Use an isolated deploy branch based on then-current main and verify full exact R9-based candidate tree. Relative to R15, remove the discarded H1/static-method/second-backbone bundle and change two R9 H2 labels; reconcile teammate changes.'})
cli('scan', '--no-interactive', name='wrapper-scan.txt')
cli('configure', '--part', 'index.html', '--metric', 'live_project_citation_rate', '--metric-goal', 'maximize',
    '--metric-command', f'python3 {ROOT / "outer_metric.py"}', '--mode', 'sequential', '--rounds', '1',
    '--metric-timeout', '120', '--no-interactive', name='wrapper-configure.txt')
run = json.loads(cli('run', '--part', 'index.html', '--no-interactive', '--json', name='wrapper-run.json'))
pool.update({'current_round': 16, 'selected_candidate_id': SELECTED, 'policy': policy,
             'updated_at': dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')})
write('candidate-pool-selected.json', pool)
assert digest(pool_path) == old_hash
pool_path.write_text(json.dumps(pool, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({'run': run, 'selected': SELECTED, 'parents': selected['parents'],
    'heading_operations': 2, 'old_proposals_preserved': 9, 'history_count': 16,
    'selection_control': 'R9 8/60 historical, not new R16 searches', 'inner_score': 'not computed'}, indent=2))
