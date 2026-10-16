"""Choose a queued cross-module candidate after the complete measured R12 record."""
import datetime as dt
import copy
import shutil
from common import *
from geo_eval.discovery import URL_RE

assert os.environ.get('SLURM_JOB_ID')
r12dir = INSTANCE / 'runs/round-12-homepage-descriptive-h1/r12-live'
current = json.loads(r12dir.joinpath('summary.json').read_text())
r12audit = json.loads(r12dir.joinpath('audit.json').read_text())
assert r12audit['passed'] and current['scheduled']['valid_responses'] == 60
assert current['decision'] == ('keep' if current['scheduled']['project_citations'] > 8 else 'discard')
seed_round = 12 if current['decision'] == 'keep' else 9
control_dir = r12dir if seed_round == 12 else INSTANCE / 'runs/round-9-static-benchmark-evidence/r9-live'
control = json.loads(control_dir.joinpath('summary.json').read_text())
base = '95940d50088176ada54ea4ed829bbf4ced9c1135' if seed_round == 12 else '52dee0ba78885b9a3028760ba8d9cfc749a6c2e7'
base_tree = control['production_tree']
assert git(SITE, 'rev-parse', 'HEAD') == base and git(SITE, 'rev-parse', 'HEAD^{tree}') == base_tree
assert not git(SITE, 'status', '--porcelain') and not git(PRODUCTION, 'status', '--porcelain')
assert git(PRODUCTION, 'rev-parse', 'HEAD') == current['production_merge_commit']
assert git(PRODUCTION, 'rev-parse', 'HEAD^{tree}') == current['production_tree']
pool_path = INSTANCE / 'candidate-pool.json'
original_hash = digest(pool_path)
pool = json.loads(pool_path.read_text())
assert pool['current_round'] == 12 and {h['id'] for h in pool['history']} == {f'r{i}' for i in range(13)}
assert len(pool['proposals']) == 8 and all(h['retain_for_combinations'] for h in pool['history'])
selected = next(p for p in pool['proposals'] if p['id'] == SELECTED)
assert selected['status'] == 'queued_unmeasured' and not selected['measured']
write('candidate-pool-before.json', pool)
original_proposal = copy.deepcopy(selected)
parents = list(selected['parents'])
if seed_round == 12:
    parents.append('r12')
selected.update({'original_proposal': original_proposal, 'round': 13, 'change_id': CHANGE_ID,
    'status': 'selected_preparing', 'base_commit': base, 'parents': parents, 'files': ['index.html'],
    'reason_selected': 'The latest complete R12 responses identify the homepage entry surface; the existing environment/agent explanations are only in script.js until a tab is selected. Test exposing those exact existing explanations in static homepage HTML, not another metadata variant.',
    'scope': 'Add one two-article static component reference inside the existing framework section. Copy titles, descriptions and knobs verbatim from the existing environment/agent JS data. Do not duplicate the default user paragraph or alter the interactive tabs.',
    'module_dependencies': ['index.html#framework and its current tab panel', 'script.js components.environment and components.agent, unchanged', 'styles.css .timescales and .knob-list, unchanged', 'R7 overview / R8 routes / R9 static results, retained'],
    'alternatives_deferred': ['static-second-backbone-evidence', 'external-paper-link-audit'],
    'interpretation': 'Unmeasured hypothesis; source presence and parent observations are not predicted intervention lift.'})
write('candidate-pool-selected.json', pool)
ROOT.joinpath('control').mkdir(exist_ok=True)
for name in ['summary.json', 'search-matrix.csv', 'search-map.json']:
    shutil.copy2(control_dir / name, ROOT / 'control' / name)
for name in ['queries.txt', 'search-map.json', 'outer_metric.py']:
    shutil.copy2(INSTANCE / 'runs/round-12-homepage-descriptive-h1' / name, ROOT / name)
assert digest(ROOT / 'queries.txt') == 'f2440c27b9fa7596e902b5bc30a30130e10789564a75f661338742d40876d8ce'
ROOT.joinpath('r12-evidence').mkdir(exist_ok=True)
engine_files = {'gpt-web': 'gpt-web-answers.jsonl', 'codex-search': 'codex-answers-complete.jsonl',
                'tavily-search': 'tavily-answers.jsonl', 'exa-search': 'exa-answers.jsonl'}
for name in ['summary.json', *engine_files.values()]:
    shutil.copy2(r12dir / name, ROOT / 'r12-evidence' / name)
queries = ROOT.joinpath('queries.txt').read_text().splitlines()
answers = {engine: {r['query']: r for r in map(json.loads, ROOT.joinpath('r12-evidence', name).read_text().splitlines())}
           for engine, name in engine_files.items()}
write('r12-search-evidence.json', {'tool': 'Preserved actual R12 four-engine responses; no R13 search calls',
    'result_scope': 'Source URLs displayed in those saved responses; not a top-ten rank or predicted lift',
    'observations': [{'query_id': f'Q{i:02d}', 'result_urls': list(dict.fromkeys(
        u.rstrip('.,;:!?*_') for engine in engine_files for u in URL_RE.findall(answers[engine][query]['text']))),
        'raw_file': 'r12-evidence/gpt-web-answers.jsonl',
        'raw_files': {engine: 'r12-evidence/' + name for engine, name in engine_files.items()}}
        for i, query in enumerate(queries, 1)]})
policy = {'primary_metric': 'live_project_citation_rate', 'goal': 'maximize',
    'definition': '100 * frozen geo_eval site_cited cells / 60, including bare project-domain occurrences under the existing judge',
    'engines': list(engine_files), 'validity': 'All 60 frozen query-engine cells must be valid; otherwise remain unranked',
    'inner_metric': 'not computed and not used',
    'baseline': f"Best measured R{seed_round}: {control['scheduled']['project_citations']}/60, composite {control['scheduled']['score']:.5f}; reused historical measurement, not a simultaneous control",
    'current_production': f"R12, {current['scheduled']['project_citations']}/60, {current['decision']}; do not lower the selection bar to current production",
    'deployment': 'Separate explicit publication approval required for R13; verify exact candidate tree and served bytes before/after 60 real probes',
    'history': 'Retain all candidates and original proposals for combinations; never add parent scores',
    'limitations': 'Immediate single samples and historical controls do not establish causality or exclude indexing lag; no automatic rollback or follow-up'}
write('outer-only-policy.json', policy)
pool.update({'current_round': 13, 'selected_candidate_id': SELECTED, 'policy': policy,
             'updated_at': dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')})
write('production-context.json', {'production_commit': current['production_merge_commit'],
    'production_tree': current['production_tree'], 'production_observation': current['scheduled'],
    'selection_seed_round': seed_round, 'selection_seed_commit': base, 'selection_seed_tree': base_tree,
    'seed_observation': control['scheduled'], 'seed_measurement_dir': str(control_dir),
    'production_unchanged': True, 'requires_separate_publication_approval': True})
write('outer-measurements.json', {'measurements': [{'label': f'r{seed_round}-best-reused-control',
    'deployed_commit': control['production_merge_commit'], 'deployed_tree': base_tree,
    'measured_at': control['measured_at'], 'query_sha256': digest(ROOT / 'queries.txt'),
    'matrix': 'control/search-matrix.csv', 'matrix_sha256': digest(ROOT / 'control/search-matrix.csv'),
    'verification': 'Exact preserved best fully measured tree; historical control, not new search collection'}]})
write('module-review.json', {'basis': 'Complete actual R12 plus R9/R10/R11 preserved outer evidence and public local source; no new R13 probes',
    'latest_observation': {'round': 12, 'citations': current['scheduled']['project_citations'],
        'explicit_project_url_cells': current['explicit_project_url_cells'],
        'explicit_support_page_url_cells': current['explicit_support_page_url_cells'],
        'decision': current['decision']},
    'reviews': [
        {'module': 'homepage-identity', 'action': f'Retain exact R{seed_round} seed identity; keep R12 result available regardless of verdict'},
        {'module': 'presentation', 'action': 'Select existing environment/agent static descriptions; preserve explorer, scripts, default user panel and results switch'},
        {'module': 'method-reference', 'action': 'Retain method.html and routes; do not infer lift from graph reach'},
        {'module': 'research-context', 'action': 'Retain factual evaluation boundaries'},
        {'module': 'paper-authority', 'action': 'Retain seed metadata; R10 candidate remains available, not silently inherited'},
        {'module': 'machine-readable-summary', 'action': 'Retain llms.txt unchanged'},
        {'module': 'crawler-routing', 'action': 'Retain robots/sitemap; no unsupported indexing claim'},
        {'module': 'repository-authority', 'action': 'Retain existing R5 README bridge'},
        {'module': 'external-paper-entry', 'action': 'Link state remains unknown; edit deferred pending separate author authority'}]})
config = {'site_url': 'https://eau-meta-agent.github.io/', 'paper_url': 'https://arxiv.org/abs/2610.16523',
    'repo_url': 'https://github.com/eau-meta-agent/eau-meta-agent.github.io',
    'platforms': {engine: .25 for engine in engine_files},
    'queries': [{'id': f'Q{i:02d}', 'text': query} for i, query in enumerate(queries, 1)],
    'interventions': [{'id': CHANGE_ID, 'candidate_id': CHANGE_ID,
        'nodes': ['file:index.html', 'section:framework', 'file:script.js', 'file:styles.css'],
        'source_url': 'https://eau-meta-agent.github.io/', 'link_state': 'present',
        'link_evidence_url': 'https://eau-meta-agent.github.io/', 'change_kind': 'node',
        'local_state': 'Environment and agent descriptions exist in script.js but require selecting their tabs',
        'hypothesis': selected['hypothesis'],
        'candidate_arms': [{'id': p['id'], 'status': p['status'], 'hypothesis': p['hypothesis']} for p in pool['proposals']]},
        {'id': 'external-paper-link-audit', 'nodes': ['external:paper-backlink'],
         'source_url': 'https://arxiv.org/abs/2610.16523', 'link_state': 'unknown', 'owner': 'paper author',
         'change_kind': 'edge', 'hypothesis': 'External author-owned paper edits require separate authority, outside R13'}]}
write('config.json', config)
write('change.json', {'round': 13, 'change_id': CHANGE_ID, 'pool_candidate_id': SELECTED,
    'state': 'preparing', 'files': ['index.html'], 'graph_nodes': ['file:index.html', 'section:framework'],
    'selection_seed_round': seed_round, 'selection_seed_commit': base, 'selection_seed_tree': base_tree,
    'current_production_commit': current['production_merge_commit'], 'current_production_tree': current['production_tree'],
    'parents': parents, 'hypothesis': selected['hypothesis'], 'selection': policy,
    'knowledge_map_sha256': digest(INSTANCE / 'map.json'),
    'unchanged_vs_seed': ['all other named sections', 'interactive component explorer', 'scripts', 'styles',
        'metadata', 'static benchmark rows', 'knowledge map', 'queries', 'judge', 'engine settings'],
    'deployment_plan': 'After separate R13 approval, apply the exact candidate index.html in an isolated deploy branch based on then-current main and verify the complete tree. Do not blindly merge a historical-seed branch into production; preserve or reconcile any teammate changes.'})
cli('scan', '--no-interactive', name='wrapper-scan.txt')
cli('configure', '--part', 'index.html', '--metric', 'live_project_citation_rate', '--metric-goal', 'maximize',
    '--metric-command', f'python3 {ROOT / "outer_metric.py"}', '--mode', 'sequential', '--rounds', '1',
    '--metric-timeout', '120', '--no-interactive', name='wrapper-configure.txt')
run = json.loads(cli('run', '--part', 'index.html', '--no-interactive', '--json', name='wrapper-run.json'))
write('candidate-pool-selected.json', pool)
assert digest(pool_path) == original_hash
pool_path.write_text(json.dumps(pool, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({'run': run, 'selected': SELECTED, 'selection_seed_round': seed_round,
    'control_citations': control['scheduled']['project_citations'], 'inner_score': 'not computed'}, indent=2))
