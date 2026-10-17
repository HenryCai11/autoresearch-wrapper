"""Propose a measured-parent combination, preserving every old candidate unchanged."""
import copy
import datetime as dt
import shutil
from common import *
from geo_eval.discovery import URL_RE

assert os.environ.get('SLURM_JOB_ID')
assert not ROOT.joinpath('wrapper-run.json').exists()
previous = INSTANCE / 'runs/round-14-static-second-backbone-evidence'
live = previous / 'r14-live'
current = json.loads(live.joinpath('summary.json').read_text())
assert json.loads(live.joinpath('audit.json').read_text())['passed']
assert current['scheduled']['valid_responses'] == 60 and current['scheduled']['project_citations'] == 5 and current['decision'] == 'discard'
base = '52dee0ba78885b9a3028760ba8d9cfc749a6c2e7'
tree = '5ebd5d1c28e00690d58caafa0edfe066ae5307d7'
assert git(SITE, 'rev-parse', 'HEAD') == base and git(SITE, 'rev-parse', 'HEAD^{tree}') == tree
assert not git(SITE, 'status', '--porcelain') and not git(PRODUCTION, 'status', '--porcelain')
assert git(PRODUCTION, 'rev-parse', 'HEAD') == current['production_merge_commit'] == 'c762ead8370159e102c5ea11b1a43b944c71d1bf'
assert git(PRODUCTION, 'rev-parse', 'HEAD^{tree}') == current['production_tree']
assert ROOT.joinpath('r14-production-index.html').read_bytes() == PRODUCTION.joinpath('index.html').read_bytes()
pool_path = INSTANCE / 'candidate-pool.json'
old_hash = digest(pool_path)
pool = json.loads(pool_path.read_text())
assert pool['current_round'] == 14 and {h['id'] for h in pool['history']} == {f'r{i}' for i in range(15)}
assert len(pool['proposals']) == 8 and SELECTED not in {p['id'] for p in pool['proposals']}
write('candidate-pool-before.json', pool)

seed_html = SITE.joinpath('index.html').read_text()
parents, operations = [], []
for number, dirname in [(12, 'round-12-homepage-descriptive-h1'), (13, 'round-13-static-component-reference'), (14, 'round-14-static-second-backbone-evidence')]:
    folder = INSTANCE / 'runs' / dirname
    parent = json.loads(folder.joinpath('change.json').read_text())
    manifest = json.loads(folder.joinpath('operations.json').read_text())
    assert len(manifest['operations']) == 1
    operation = manifest['operations'][0]
    assert operation['op'] == 'replace_text' and operation['node'] == 'file:index.html'
    assert seed_html.count(operation['before']) == 1
    exact_parent = subprocess.check_output(['git', '-C', str(SITE), 'show', parent['candidate_commit'] + ':index.html'], text=True)
    assert exact_parent == seed_html.replace(operation['before'], operation['after'], 1)
    assert git(SITE, 'rev-parse', parent['candidate_commit'] + '^{tree}') == parent['candidate_tree']
    destination = ROOT / f'parents/r{number}-operations.json'
    destination.parent.mkdir(exist_ok=True)
    shutil.copy2(folder / 'operations.json', destination)
    parents.append({'round': number, 'candidate_commit': parent['candidate_commit'], 'candidate_tree': parent['candidate_tree'],
        'operations': f'parents/r{number}-operations.json', 'operations_sha256': digest(destination),
        'parent_effect': 'discard in its single historical observation; not an isolated causal effect',
        'exact_parent_html_reproduced_from_r9': True})
    operations.append(operation)
write('combination-source.json', {'seed_commit': base, 'parents': parents, 'operation_count': 3,
    'hypothesis': 'Present the existing entity name, environment/agent method descriptions, and both result backbones together in initial HTML.',
    'score_policy': 'Combination is unmeasured. Do not add parent scores or infer lift from source presence or previous discards.'})
write('operations.json', {'operations': operations})
selected = {'id': SELECTED, 'status': 'selected_preparing', 'measured': False, 'round': 15,
    'change_id': CHANGE_ID, 'parents': ['r9', 'r12', 'r13', 'r14'], 'retain_for_combinations': True,
    'modules': ['homepage-identity', 'presentation', 'method-reference'], 'files': ['index.html'], 'base_commit': base,
    'hypothesis': 'Test whether the retained R12 H1, R13 static method explanations and R14 second-backbone table work together as an initial-HTML identity/method/evidence bundle on R9.',
    'reason_selected': 'All seven editable-site proposals now have observations. The only remaining unmeasured old proposal needs external author authority. A separately identified combination tests previously retained candidates without deleting or overwriting their individual results.',
    'scope': 'Replay exactly three archived operations; no new wording, numbers, styles, scripts or schema.',
    'module_dependencies': ['index.html hero-title, framework and results', 'existing script.js component/result facts, unchanged', 'existing styles.css, unchanged', 'R7 overview, R8 references and R9 default static data, retained'],
    'interpretation': 'Unmeasured bundle, not predicted lift. Single immediate historical observations cannot isolate parent effects or rule out indexing lag.'}
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
policy.update({'current_production': 'R14 unchanged, 5/60, composite 28.88889, discard; not the selection threshold',
    'baseline': 'Best complete R9, 8/60, composite 30.25; reused historical control, not fresh/simultaneous',
    'deployment': 'Separate explicit R15 approval required, exact candidate tree and served bytes verified before/after all 60 real requests',
    'history': 'All eight old proposals and 15 old history entries are unchanged; one new combination proposal is separate and unmeasured; do not add parent scores'})
write('outer-only-policy.json', policy)
engine_files = {'gpt-web': 'gpt-web-answers.jsonl', 'codex-search': 'codex-answers-complete.jsonl',
                'tavily-search': 'tavily-answers.jsonl', 'exa-search': 'exa-answers.jsonl'}
ROOT.joinpath('r14-evidence').mkdir(exist_ok=True)
for name in ['summary.json', *engine_files.values()]:
    shutil.copy2(live / name, ROOT / 'r14-evidence' / name)
queries = ROOT.joinpath('queries.txt').read_text().splitlines()
answers = {engine: {r['query']: r for r in map(json.loads, ROOT.joinpath('r14-evidence', name).read_text().splitlines())} for engine,name in engine_files.items()}
write('r14-search-evidence.json', {'tool': 'Saved actual R14 four-engine answers; not new R15 probes',
    'result_scope': 'Displayed source URLs only, not top-ten ranks or predicted intervention lift',
    'observations': [{'query_id': f'Q{i:02d}', 'result_urls': list(dict.fromkeys(u.rstrip('.,;:!?*_') for engine in engine_files for u in URL_RE.findall(answers[engine][query]['text']))),
        'raw_file': 'r14-evidence/gpt-web-answers.jsonl',
        'raw_files': {engine: 'r14-evidence/' + name for engine,name in engine_files.items()}} for i,query in enumerate(queries, 1)]})
actions = {'homepage-identity': 'Replay R12 existing EAU/co-evolution H1, preserving the full subtitle',
    'presentation': 'Replay existing static method and result blocks; scripts/styles unchanged',
    'method-reference': 'R13 homepage component descriptions combined; method.html unchanged',
    'research-context': 'Retain scope and evaluation boundaries unchanged',
    'paper-authority': 'Retain R9 metadata; no new measurements, gains, authors or claims',
    'machine-readable-summary': 'Retain llms.txt unchanged',
    'repository-authority': 'Retain existing README bridge; no external repository mutation',
    'crawler-routing': 'Retain robots/sitemap; no claim that served content proves indexing',
    'reference-pages': 'Retain R8 routes; R14 returned no explicit support-page URLs',
    'external-paper-entry': 'Unknown backlink state; any edit requires separate author authority'}
assert set(actions) == {m['id'] for m in pool['modules']}
write('module-review.json', {'basis': 'Measured R14 plus preserved R9/R12/R13 and exact archived parent operations; no new R15 searches',
    'latest_observation': {'round': 14, 'citations': 5, 'explicit_project_url_cells': 3, 'explicit_support_page_url_cells': 0, 'decision': 'discard'},
    'reviews': [{'module': key, 'action': value} for key,value in actions.items()],
    'selection_limit': 'A bundle result cannot identify individual module effects; immediate search observations may reflect stale indexes.'})
config = json.loads(previous.joinpath('config.json').read_text())
config['interventions'][0] = {'id': CHANGE_ID, 'candidate_id': CHANGE_ID,
    'nodes': ['file:index.html', 'section:framework', 'section:results', 'file:script.js', 'file:styles.css'],
    'source_url': 'https://eau-meta-agent.github.io/', 'link_state': 'present', 'link_evidence_url': 'https://eau-meta-agent.github.io/',
    'change_kind': 'node', 'local_state': 'On R9, semantic H1 and nondefault component/result content are not all present together in initial HTML',
    'hypothesis': selected['hypothesis'], 'candidate_arms': [{'id': p['id'], 'status': p['status'], 'hypothesis': p['hypothesis']} for p in pool['proposals']]}
config['interventions'][1]['hypothesis'] = 'External paper edits require separate authority and are outside R15'
write('config.json', config)
write('change.json', {'round': 15, 'change_id': CHANGE_ID, 'pool_candidate_id': SELECTED, 'state': 'preparing',
    'files': ['index.html'], 'graph_nodes': ['file:index.html', 'section:framework', 'section:results'],
    'selection_seed_round': 9, 'selection_seed_commit': base, 'selection_seed_tree': tree,
    'current_production_commit': current['production_merge_commit'], 'current_production_tree': current['production_tree'],
    'parents': selected['parents'], 'hypothesis': selected['hypothesis'], 'selection': policy,
    'knowledge_map_sha256': digest(INSTANCE / 'map.json'),
    'unchanged_vs_seed': ['all bytes except the three exact archived operations', 'all other pages', 'R7 overview and R8 links', 'default result rows and switch', 'scripts', 'styles', 'metadata', 'map', 'queries', 'judge', 'engine settings'],
    'deployment_plan': 'Require separate R15 approval. Use an isolated deploy branch based on then-current main, apply exact candidate index.html and verify its whole tree; reconcile teammate changes. Relative to R14, the second-backbone table remains unchanged and H1 plus component descriptions are added.'})
cli('scan', '--no-interactive', name='wrapper-scan.txt')
cli('configure', '--part', 'index.html', '--metric', 'live_project_citation_rate', '--metric-goal', 'maximize',
    '--metric-command', f'python3 {ROOT / "outer_metric.py"}', '--mode', 'sequential', '--rounds', '1',
    '--metric-timeout', '120', '--no-interactive', name='wrapper-configure.txt')
run = json.loads(cli('run', '--part', 'index.html', '--no-interactive', '--json', name='wrapper-run.json'))
pool.update({'current_round': 15, 'selected_candidate_id': SELECTED, 'policy': policy,
             'updated_at': dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')})
write('candidate-pool-selected.json', pool)
assert digest(pool_path) == old_hash
pool_path.write_text(json.dumps(pool, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({'run': run, 'selected': SELECTED, 'parents': selected['parents'], 'parent_operations_exactly_reproduced': 3,
    'old_proposals_preserved': 8, 'selection_control': 'R9 8/60 historical, not new R15 searches', 'inner_score': 'not computed'}, indent=2))
