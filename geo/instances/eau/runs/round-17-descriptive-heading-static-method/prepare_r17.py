"""Prepare R16 headings + exact retained R13 method HTML; do not infer parent lift."""
import copy
import datetime as dt
import shutil
from common import *
from geo_eval.discovery import URL_RE

assert os.environ.get('SLURM_JOB_ID')
assert not ROOT.joinpath('wrapper-run.json').exists(), 'Do not start a second R17 run'
pool_path = INSTANCE / 'candidate-pool.json'
old_hash = digest(pool_path)
pool = json.loads(pool_path.read_text())
assert pool['current_round'] == 16 and {h['id'] for h in pool['history']} == {f'r{i}' for i in range(17)}
assert len(pool['proposals']) == 10 and SELECTED not in {p['id'] for p in pool['proposals']}
best = copy.deepcopy(pool['best_observed'])
assert best['round'] == 16 and best['decision'] == 'keep' and best['outer_observation']['project_citations'] == 9
previous = INSTANCE / 'runs/round-16-descriptive-section-headings'
live = INSTANCE / best['artifact_dir']
current = json.loads(live.joinpath('summary.json').read_text())
assert json.loads(live.joinpath('audit.json').read_text())['passed']
assert current['scheduled']['valid_responses'] == 60 and current['scheduled']['project_citations'] == 9 and current['decision'] == 'keep'
assert best['outer_observation'] == current['scheduled']
base = best['candidate_commit']
tree = best['candidate_tree']
assert base == '18c0ae3d6af0baf151487681aac40d7a09dd475c' and tree == '692b95a10e27de1e9c84011fb839cba3b0eb6b15'
assert git(SITE, 'rev-parse', 'HEAD') == base and git(SITE, 'rev-parse', 'HEAD^{tree}') == tree
assert not git(SITE, 'status', '--porcelain') and not git(PRODUCTION, 'status', '--porcelain')
assert git(PRODUCTION, 'rev-parse', 'HEAD') == current['production_merge_commit'] == 'ff79a10c4e93906cad803be5e23580f60bd98412'
assert git(PRODUCTION, 'rev-parse', 'HEAD^{tree}') == current['production_tree'] == tree
assert ROOT.joinpath('r16-production-index.html').read_bytes() == PRODUCTION.joinpath('index.html').read_bytes() == SITE.joinpath('index.html').read_bytes()
write('candidate-pool-before.json', pool)

retained = INSTANCE / 'runs/round-13-static-component-reference'
parent13 = json.loads(retained.joinpath('change.json').read_text())
parent16 = json.loads(previous.joinpath('change.json').read_text())
op13 = json.loads(retained.joinpath('operations.json').read_text())['operations']
op16 = json.loads(previous.joinpath('operations.json').read_text())['operations']
assert len(op13) == 1 and len(op16) == 2
assert op13[0]['op'] == 'replace_text' and op13[0]['node'] == 'file:index.html'
r9_html = subprocess.check_output(['git', '-C', str(SITE), 'show', '52dee0ba78885b9a3028760ba8d9cfc749a6c2e7:index.html'], text=True)
r13_html = subprocess.check_output(['git', '-C', str(SITE), 'show', parent13['candidate_commit'] + ':index.html'], text=True)
assert r9_html.count(op13[0]['before']) == 1 and r9_html.replace(op13[0]['before'], op13[0]['after'], 1) == r13_html
assert git(SITE, 'rev-parse', parent13['candidate_commit'] + '^{tree}') == parent13['candidate_tree']
replayed16 = r9_html
for op in op16:
    assert replayed16.count(op['before']) == 1
    replayed16 = replayed16.replace(op['before'], op['after'], 1)
assert replayed16 == SITE.joinpath('index.html').read_text()
assert replayed16.count(op13[0]['before']) == 1
ROOT.joinpath('parents').mkdir(exist_ok=True)
shutil.copy2(retained / 'operations.json', ROOT / 'parents/r13-operations.json')
shutil.copy2(previous / 'operations.json', ROOT / 'parents/r16-operations.json')
shutil.copy2(retained / 'operations.json', ROOT / 'operations.json')
write('combination-source.json', {'seed_round': 16, 'seed_commit': base, 'seed_tree': tree,
    'parents': [
        {'round': 16, 'candidate_commit': base, 'candidate_tree': tree, 'operations': 'parents/r16-operations.json',
         'operations_sha256': digest(ROOT / 'parents/r16-operations.json'), 'applied_as': 'already in the measured seed; do not apply twice'},
        {'round': 13, 'candidate_commit': parent13['candidate_commit'], 'candidate_tree': parent13['candidate_tree'],
         'operations': 'parents/r13-operations.json', 'operations_sha256': digest(ROOT / 'parents/r13-operations.json'),
         'applied_as': 'one exact archived operation added on R16'}],
    'applied_operation_count': 1, 'inherited_heading_operation_count': 2,
    'r13_full_html_reproduced_from_r9': True, 'r16_full_html_reproduced_from_r9': True,
    'score_policy': 'New unmeasured combination. R13 discard and R16 keep are historical observations, not isolated effects; do not add scores or predict lift.'})
selected = {'id': SELECTED, 'status': 'selected_preparing', 'measured': False, 'round': 17,
    'change_id': CHANGE_ID, 'parents': ['r16', 'r13'], 'retain_for_combinations': True,
    'modules': ['homepage-identity', 'presentation', 'method-reference'], 'files': ['index.html'], 'base_commit': base,
    'hypothesis': 'Test the exact retained R13 static environment/agent explanations under R16 descriptive section headings, with no new wording or facts.',
    'reason_selected': 'R16 has 9/60 citations but zero fuzzy-tier citations and eight explicit homepage URL cells with no support-page URLs. Test passage completeness at that observed homepage surface; source visibility is not a lift estimate.',
    'scope': 'One archived replace_text operation; no R12 H1, R14 second-backbone table, new text, data, claims, links, scripts, styles or schema.',
    'module_dependencies': ['R16 framework-title and results-title retained', 'unchanged script.js component facts',
        'existing timescales/knob-list CSS', 'interactive tabs and R9 default static results unchanged'],
    'interpretation': 'Unmeasured combination, not predicted lift; the R13 7/60 and R15 6/60 historical samples are not added to R16 9/60.'}
pool['proposals'].append(selected)
write('new-proposals.json', [selected])

ROOT.joinpath('control').mkdir(exist_ok=True)
for name in ['summary.json', 'search-matrix.csv', 'search-map.json']:
    shutil.copy2(live / name, ROOT / 'control' / name)
for name in ['outer_metric.py', 'queries.txt', 'search-map.json']:
    shutil.copy2(previous / name, ROOT / name)
shutil.copy2(live / 'collection-settings.json', ROOT / 'collection-settings.json')
assert digest(ROOT / 'queries.txt') == 'f2440c27b9fa7596e902b5bc30a30130e10789564a75f661338742d40876d8ce'
assert digest(ROOT / 'control/search-matrix.csv') == 'c45ff1cb3c6c30f7920357cfbdea3b60ffe53ea9730d11428c6c6e569997008e'
registry = json.loads(previous.joinpath('outer-measurements.json').read_text())
measurements = [r for r in registry['measurements'] if r['deployed_tree'] == tree]
assert len(measurements) == 1 and measurements[0]['label'] == 'r16-immediate-live'
control_record = copy.deepcopy(measurements[0])
control_record.update({'label': 'r16-best-reused-control', 'source_label': 'r16-immediate-live',
    'matrix': 'control/search-matrix.csv', 'measured_at': current['measured_at'],
    'verification': 'Exact preserved best fully measured R16 tree; historical control, not new R17 searches'})
write('outer-measurements.json', {'measurements': [control_record]})
write('production-context.json', {'production_commit': current['production_merge_commit'], 'production_tree': tree,
    'production_observation': current['scheduled'], 'selection_seed_round': 16, 'selection_seed_commit': base,
    'selection_seed_tree': tree, 'seed_observation': current['scheduled'],
    'best_observed_before': best, 'production_unchanged': True, 'requires_separate_publication_approval': True})
policy = copy.deepcopy(pool['policy'])
policy.update({'baseline': 'Best complete R16, 9/60, composite 31.86111; reused historical control, not fresh/simultaneous. Keep requires strictly more than 9/60.',
    'current_production': 'R16 unchanged, 9/60, keep; exact best observed seed',
    'deployment': 'Separate explicit R17 approval required; verify exact candidate tree and served bytes before/after all 60 real requests',
    'history': 'All ten old proposals, 17 old history entries and best_observed R16 unchanged; one separate combination proposal is unmeasured. Never add parent scores.'})
write('outer-only-policy.json', policy)
engine_files = {'gpt-web': 'gpt-web-answers.jsonl', 'codex-search': 'codex-answers-complete.jsonl',
                'tavily-search': 'tavily-answers.jsonl', 'exa-search': 'exa-answers.jsonl'}
ROOT.joinpath('r16-evidence').mkdir(exist_ok=True)
for name in ['summary.json', *engine_files.values()]:
    shutil.copy2(live / name, ROOT / 'r16-evidence' / name)
queries = ROOT.joinpath('queries.txt').read_text().splitlines()
answers = {engine: {r['query']: r for r in map(json.loads, ROOT.joinpath('r16-evidence', name).read_text().splitlines())} for engine,name in engine_files.items()}
assert all(len(rows) == 15 and set(rows) == set(queries) and all(row['status'] == 'ok' for row in rows.values()) for rows in answers.values())
write('r16-search-evidence.json', {'tool': 'Saved actual R16 four-engine answers; not new R17 probes',
    'result_scope': 'Displayed source URLs only, not top-ten ranks or predicted intervention lift',
    'observations': [{'query_id': f'Q{i:02d}', 'result_urls': list(dict.fromkeys(u.rstrip('.,;:!?*_') for engine in engine_files for u in URL_RE.findall(answers[engine][query]['text']))),
        'raw_file': 'r16-evidence/gpt-web-answers.jsonl',
        'raw_files': {engine: 'r16-evidence/' + name for engine,name in engine_files.items()}} for i,query in enumerate(queries, 1)]})
actions = {'homepage-identity': 'Keep R16 H2s and existing H1/subtitle; no replay of discarded R12 hero change',
    'presentation': 'Exact R13 persistent articles under descriptive method heading; reuse existing CSS and preserve interactive tabs',
    'method-reference': 'Reuse existing environment/agent facts verbatim from script.js; method.html unchanged',
    'research-context': 'Retain existing scope and evaluation-boundary text; no new topic block',
    'paper-authority': 'Retain metadata/evidence and all result numbers; no R14 second-backbone reference table',
    'machine-readable-summary': 'Retain llms.txt; no measured support-page URL retrieval in R16',
    'repository-authority': 'Retain existing README bridge; no external repository mutation',
    'crawler-routing': 'Retain robots/sitemap; served content does not prove indexing',
    'reference-pages': 'Retain R8 routes; no extra links, schema, or reference-page expansion',
    'external-paper-entry': 'Unknown backlink state; any edit still needs separate author authority'}
assert set(actions) == {m['id'] for m in pool['modules']}
write('module-review.json', {'basis': 'Actual complete R16 outer measurement plus preserved R13/R15 observations; no new R17 searches',
    'latest_observation': {'round': 16, 'citations': 9, 'explicit_project_url_cells': 8, 'explicit_support_page_url_cells': 0,
        'fuzzy_citations': current['by_tier']['fuzzy']['project_citations'], 'broad_citations': current['by_tier']['broad']['project_citations'], 'decision': 'keep'},
    'reviews': [{'module': key, 'action': value} for key,value in actions.items()],
    'alternatives_retained': [
        {'ids': ['static-component-reference'], 'action': 'Exact R13 operation reused in a new proposal, leaving the original measured discard untouched'},
        {'ids': ['homepage-descriptive-h1', 'static-second-backbone-evidence', 'static-entry-combination'],
         'action': 'Retain R12/R14/R15 observations for later tests; do not silently inherit their full bundles'},
        {'ids': ['shared-scholarly-entity', 'reference-cluster-without-r7', 'r8-reference-cluster'], 'action': 'Retain previous schema/routing/overview candidates without assigning causal effects'},
        {'ids': ['external-paper-link-audit'], 'action': 'Unknown, unmeasured, outside edit authority'}],
    'selection_limit': 'R16 source visibility does not predict combination lift. Historical single samples cannot isolate modules or rule out stale indexes.'})
config = json.loads(previous.joinpath('config.json').read_text())
config['interventions'][0] = {'id': CHANGE_ID, 'candidate_id': CHANGE_ID,
    'nodes': ['file:index.html', 'section:framework', 'file:script.js', 'file:styles.css'],
    'source_url': 'https://eau-meta-agent.github.io/', 'link_state': 'present', 'link_evidence_url': 'https://eau-meta-agent.github.io/',
    'change_kind': 'node', 'local_state': 'R16 descriptive heading is visible, but environment/agent explanations still require tab interaction',
    'hypothesis': selected['hypothesis'], 'candidate_arms': [{'id': p['id'], 'status': p['status'], 'hypothesis': p['hypothesis']} for p in pool['proposals']]}
config['interventions'][1]['hypothesis'] = 'External paper edits require separate authority and are outside R17'
write('config.json', config)
write('change.json', {'round': 17, 'change_id': CHANGE_ID, 'pool_candidate_id': SELECTED, 'state': 'preparing',
    'files': ['index.html'], 'graph_nodes': ['file:index.html', 'section:framework'],
    'selection_seed_round': 16, 'selection_seed_commit': base, 'selection_seed_tree': tree,
    'current_production_commit': current['production_merge_commit'], 'current_production_tree': tree,
    'parents': selected['parents'], 'hypothesis': selected['hypothesis'], 'selection': policy,
    'knowledge_map_sha256': digest(INSTANCE / 'map.json'),
    'unchanged_vs_seed': ['all bytes except one exact retained R13 insertion', 'both R16 H2s', 'H1/subtitle', 'R7 overview', 'R8 routes', 'R9 static default data',
        'other sections/pages', 'existing interactive explorer', 'scripts', 'styles', 'metadata', 'map', 'queries', 'judge', 'engine settings'],
    'deployment_plan': 'Require separate R17 approval. Starting from then-current main, apply the exact R16-based candidate and verify its complete tree; reconcile teammate changes. Only one static method-reference insertion differs from current R16.'})
cli('scan', '--no-interactive', name='wrapper-scan.txt')
cli('configure', '--part', 'index.html', '--metric', 'live_project_citation_rate', '--metric-goal', 'maximize',
    '--metric-command', f'python3 {ROOT / "outer_metric.py"}', '--mode', 'sequential', '--rounds', '1',
    '--metric-timeout', '120', '--no-interactive', name='wrapper-configure.txt')
run = json.loads(cli('run', '--part', 'index.html', '--no-interactive', '--json', name='wrapper-run.json'))
pool.update({'current_round': 17, 'selected_candidate_id': SELECTED, 'policy': policy,
             'updated_at': dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')})
assert pool['best_observed'] == best
write('candidate-pool-selected.json', pool)
assert digest(pool_path) == old_hash
pool_path.write_text(json.dumps(pool, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({'run': run, 'selected': SELECTED, 'parents': selected['parents'], 'seed_round': 16,
    'old_proposals_preserved': 10, 'history_count': 17, 'applied_operations': 1,
    'selection_control': 'R16 9/60 historical; no new R17 searches', 'inner_score': 'not computed'}, indent=2))
