"""Prepare one user-requested outbound-paper-routing bundle on measured R17."""
import copy
import datetime as dt
import re
import shutil
from common import *
from geo_eval.discovery import URL_RE

assert os.environ.get('SLURM_JOB_ID')
assert not ROOT.joinpath('wrapper-run.json').exists(), 'Do not start a second R18 run'
pool_path = INSTANCE / 'candidate-pool.json'
old_hash = digest(pool_path)
pool = json.loads(pool_path.read_text())
assert pool['current_round'] == 17 and {h['id'] for h in pool['history']} == {f'r{i}' for i in range(18)}
assert len(pool['proposals']) == 11 and SELECTED not in {p['id'] for p in pool['proposals']}
best = copy.deepcopy(pool['best_observed'])
assert best['round'] == 17 and best['decision'] == 'keep' and best['outer_observation']['project_citations'] == 10
previous = INSTANCE / 'runs/round-17-descriptive-heading-static-method'
live = INSTANCE / best['artifact_dir']
current = json.loads(live.joinpath('summary.json').read_text())
assert json.loads(live.joinpath('audit.json').read_text())['passed']
assert current['scheduled']['valid_responses'] == 60 and current['scheduled']['project_citations'] == 10
assert best['outer_observation'] == current['scheduled'] and current['decision'] == 'keep'
base, tree = best['candidate_commit'], best['candidate_tree']
assert base == 'dcf0b80e0e0554746e94e3e47034d77174b35417' and tree == 'acbe04ac17e69189e3eb630ed9c89e449b8faa44'
assert git(SITE, 'rev-parse', 'HEAD') == base and git(SITE, 'rev-parse', 'HEAD^{tree}') == tree
assert not git(SITE, 'status', '--porcelain') and not git(PRODUCTION, 'status', '--porcelain')
assert git(PRODUCTION, 'rev-parse', 'HEAD') == current['production_merge_commit'] == '6eb91c2d44003afe248e5e2623a2a6a2f38f5675'
assert git(PRODUCTION, 'rev-parse', 'HEAD^{tree}') == current['production_tree'] == tree
assert ROOT.joinpath('r17-production-index.html').read_bytes() == PRODUCTION.joinpath('index.html').read_bytes() == SITE.joinpath('index.html').read_bytes()
write('candidate-pool-before.json', pool)

page = ROOT.joinpath('alphaxiv-page.html').read_text()
title = re.search(r'<title>([^<]+)</title>', page)[1]
canonical = re.search(r'<link rel="canonical" href="([^"]+)"', page)[1]
paper_id = re.search(r'<meta name="citation_arxiv_id" content="([^"]+)"', page)[1]
assert title == 'EAU: Environment-Agent-User Co-evolution for Training User-Centric Agents | alphaXiv'
assert canonical == ALPHA and paper_id == '2610.16523'
assert re.search(r'HTTP/[\d.]+ 200', ROOT.joinpath('alphaxiv-headers.txt').read_text())
write('alphaxiv-verification.json', {'url': ALPHA, 'http_status': 200, 'canonical': canonical,
    'title': title, 'arxiv_id': paper_id, 'body_sha256': digest(ROOT / 'alphaxiv-page.html'),
    'verified_at': dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds'),
    'scope': 'Public title, canonical and paper ID only; no external edit, ownership claim, backlink or traffic measurement',
    'body_location': 'Scratch verification only; full third-party page not copied to permanent archive'})

operations = []
def op(file, before, after):
    assert SITE.joinpath(file).read_text().count(before) == 1, (file, before)
    operations.append({'op': 'replace_text', 'node': 'file:' + file, 'before': before, 'after': after})

op('index.html', f'<a href="{PAPER}">arXiv:2610.16523</a>', f'<a href="{ALPHA}">alphaXiv (arXiv:2610.16523)</a>')
op('index.html', f'<a class="button button-dark" href="{PAPER}" target="_blank" rel="noopener">arXiv <span',
   f'<a class="button button-dark" href="{ALPHA}" target="_blank" rel="noopener">alphaXiv <span')
op('index.html', f'<a class="button button-dark" href="{PAPER}" target="_blank" rel="noopener">Read on arXiv <span',
   f'<a class="button button-dark" href="{ALPHA}" target="_blank" rel="noopener">Read on alphaXiv <span')
for file, label in [('paper.html', 'arXiv'), ('method.html', 'Paper'), ('research-context.html', 'Paper')]:
    op(file, f'<a class="header-link" href="{PAPER}">{label} <span', f'<a class="header-link" href="{ALPHA}">alphaXiv <span')
op('llms.txt', f'- Paper: {PAPER}', f'- Paper (alphaXiv): {ALPHA}')
op('README.md', f'- **Paper:** [arXiv:2610.16523]({PAPER})', f'- **Paper:** [alphaXiv — arXiv:2610.16523]({ALPHA})')
op('site-config.js', f'paperUrl: "{PAPER}"', f'paperUrl: "{ALPHA}"')
assert len(operations) == 9 and sorted({o['node'][5:] for o in operations}) == FILES
supported = {'index.html', 'README.md', 'site-config.js'}
write('operations.json', {'operations': operations})
write('wrapper-operations.json', {'operations': [o for o in operations if o['node'][5:] in supported]})
write('manual-operations.json', {'reason': 'Existing geo-graph does not expose support HTML or llms.txt file nodes; main agent applies these four exact replacements with apply_patch inside the allocated worktree. No wrapper-core extension.',
    'operations': [o for o in operations if o['node'][5:] not in supported]})
selected = {'id': SELECTED, 'status': 'selected_preparing', 'measured': False, 'round': 18,
    'change_id': CHANGE_ID, 'parents': ['r17'], 'retain_for_combinations': True,
    'modules': ['homepage-identity', 'method-reference', 'research-context', 'paper-authority',
        'machine-readable-summary', 'repository-authority', 'presentation', 'reference-pages'],
    'files': FILES, 'base_commit': base,
    'hypothesis': 'Route paper-reading entry points consistently to the verified alphaXiv paper as requested by the user, while preserving scholarly identifiers and testing any project-site discovery change separately.',
    'reason_selected': 'Explicit user traffic-routing request; not selected from inferred GEO lift or an inner score.',
    'scope': 'Nine exact URL/label replacements in seven website files; no independent content, result, style, schema or external-page edit.',
    'module_dependencies': ['All six static HTML anchors use alphaXiv', 'site-config.js uses the same destination',
        'llms.txt and README paper entry agree', 'arXiv PDF, citation metadata, JSON-LD identity, CITATION.cff and both BibTeX blocks unchanged'],
    'interpretation': 'alphaXiv clicks/visits are not measured by the project-domain citation matrix. No traffic gain or discovery lift is assumed.'}
pool['proposals'].append(selected)
write('new-proposals.json', [selected])

ROOT.joinpath('control').mkdir(exist_ok=True)
for name in ['summary.json', 'search-matrix.csv', 'search-map.json']:
    shutil.copy2(live / name, ROOT / 'control' / name)
for name in ['outer_metric.py', 'queries.txt', 'search-map.json']:
    shutil.copy2(previous / name, ROOT / name)
shutil.copy2(live / 'collection-settings.json', ROOT / 'collection-settings.json')
assert digest(ROOT / 'queries.txt') == 'f2440c27b9fa7596e902b5bc30a30130e10789564a75f661338742d40876d8ce'
assert digest(ROOT / 'control/search-matrix.csv') == 'b70606920db1af4346d6ec93cc84491d3f778c6249aaba6d4423686785ec090c'
registry = json.loads(previous.joinpath('outer-measurements.json').read_text())
measurements = [r for r in registry['measurements'] if r['deployed_tree'] == tree]
assert len(measurements) == 1 and measurements[0]['label'] == 'r17-immediate-live'
control_record = copy.deepcopy(measurements[0])
control_record.update({'label': 'r17-best-reused-control', 'source_label': 'r17-immediate-live',
    'matrix': 'control/search-matrix.csv', 'measured_at': current['measured_at'],
    'verification': 'Exact preserved best fully measured R17 tree; historical control, not new R18 searches'})
write('outer-measurements.json', {'measurements': [control_record]})
write('production-context.json', {'production_commit': current['production_merge_commit'], 'production_tree': tree,
    'production_observation': current['scheduled'], 'selection_seed_round': 17, 'selection_seed_commit': base,
    'selection_seed_tree': tree, 'seed_observation': current['scheduled'], 'best_observed_before': best,
    'production_unchanged': True, 'requires_separate_publication_approval': True})
policy = copy.deepcopy(pool['policy'])
policy.update({'baseline': 'Best complete R17, 10/60, composite 34.30556; reused historical control, not fresh/simultaneous. Keep requires strictly more than 10/60.',
    'current_production': 'R17 unchanged, 10/60, keep; exact best observed seed',
    'deployment': 'Separate explicit R18 approval required; verify exact complete candidate tree and all seven changed served resources before/after the real 60 requests',
    'history': 'All eleven old proposals, 18 old observations and best_observed R17 unchanged; one new user-requested routing proposal is unmeasured. Never add parent scores.'})
write('outer-only-policy.json', policy)
engine_files = {'gpt-web': 'gpt-web-answers.jsonl', 'codex-search': 'codex-answers-complete.jsonl',
                'tavily-search': 'tavily-answers.jsonl', 'exa-search': 'exa-answers.jsonl'}
ROOT.joinpath('r17-evidence').mkdir(exist_ok=True)
for name in ['summary.json', *engine_files.values()]:
    shutil.copy2(live / name, ROOT / 'r17-evidence' / name)
queries = ROOT.joinpath('queries.txt').read_text().splitlines()
answers = {engine: {r['query']: r for r in map(json.loads, ROOT.joinpath('r17-evidence', name).read_text().splitlines())} for engine,name in engine_files.items()}
assert all(len(rows) == 15 and set(rows) == set(queries) and all(row['status'] == 'ok' for row in rows.values()) for rows in answers.values())
write('r17-search-evidence.json', {'tool': 'Saved actual R17 four-engine answers; not new R18 probes',
    'result_scope': 'Displayed source URLs only, not top-ten ranks, traffic counts or predicted routing lift',
    'observations': [{'query_id': f'Q{i:02d}', 'result_urls': list(dict.fromkeys(u.rstrip('.,;:!?*_') for engine in engine_files for u in URL_RE.findall(answers[engine][query]['text']))),
        'raw_file': 'r17-evidence/gpt-web-answers.jsonl',
        'raw_files': {engine: 'r17-evidence/' + name for engine,name in engine_files.items()}} for i,query in enumerate(queries, 1)]})
actions = {'homepage-identity': 'Route three visible paper anchors and labels to alphaXiv; retain R17 H1, R16 H2s, R7 overview and project self-links',
    'presentation': 'Align existing paperUrl configuration; do not change script.js, CSS, layout or tracking',
    'method-reference': 'Route header paper link only; retain R13 persistent method block inherited by R17',
    'research-context': 'Route header paper link only; scope/comparison text unchanged',
    'paper-authority': 'Route header paper link only; preserve arXiv identity, PDF, schema, authors and benchmark facts',
    'machine-readable-summary': 'Align llms.txt Paper entry with alphaXiv; all factual text unchanged',
    'repository-authority': 'Align website-repository README Paper entry; preserve BibTeX, no external repository edit',
    'crawler-routing': 'Retain robots/sitemap; do not imply alphaXiv traffic or indexing is measured',
    'reference-pages': 'Retain R8 routes and project-domain links; align support-page paper destinations',
    'external-paper-entry': 'Public alphaXiv identity verified; external backlink state remains unknown and no external edit is authorized'}
assert set(actions) == {m['id'] for m in pool['modules']}
write('module-review.json', {'basis': 'Explicit user routing request, complete R17 outer history, and independent public alphaXiv URL verification; no new eval probes',
    'latest_observation': {'round': 17, 'citations': 10, 'explicit_project_url_cells': 9, 'explicit_support_page_url_cells': 0,
        'fuzzy_citations': current['by_tier']['fuzzy']['project_citations'], 'broad_citations': current['by_tier']['broad']['project_citations'], 'decision': 'keep'},
    'reviews': [{'module': key, 'action': value} for key,value in actions.items()],
    'alternatives_retained': [{'ids': [p['id'] for p in pool['proposals'] if p['id'] != SELECTED],
        'action': 'All eleven old proposals and eighteen measured histories retained unchanged. Keep R17 composition as seed; do not mix in R12 H1, R14 table, discarded schema/overview variants or external edits.'}],
    'selection_limit': 'Outbound traffic-routing goal is not the project-domain metric; alphaXiv is not counted as the project site. Historical observations do not predict lift.'})
config = json.loads(previous.joinpath('config.json').read_text())
config['alphaxiv_url'] = ALPHA
config['interventions'][0] = {'id': CHANGE_ID, 'candidate_id': CHANGE_ID,
    'nodes': ['file:index.html', 'file:README.md', 'file:site-config.js'],
    'manual_files': ['llms.txt', 'method.html', 'paper.html', 'research-context.html'],
    'graph_scope': 'Five operations on three existing graph nodes; four support-file replacements via apply_patch, explicit manifest and validation. No core graph extension.',
    'source_url': 'https://eau-meta-agent.github.io/', 'link_state': 'present', 'link_evidence_url': 'https://eau-meta-agent.github.io/',
    'change_kind': 'edge', 'local_state': 'Site-owned paper entry points currently route to arXiv; verified alphaXiv URL available',
    'hypothesis': selected['hypothesis'],
    'candidate_arms': [{'id': p['id'], 'status': p['status'], 'hypothesis': p['hypothesis']} for p in pool['proposals']]}
config['interventions'][1]['hypothesis'] = 'External paper edits require separate authority and are outside R18; changing a site-owned outbound link is not editing an external backlink'
write('config.json', config)
write('change.json', {'round': 18, 'change_id': CHANGE_ID, 'pool_candidate_id': SELECTED, 'state': 'preparing',
    'files': FILES, 'graph_nodes': config['interventions'][0]['nodes'], 'manual_files': config['interventions'][0]['manual_files'],
    'selection_seed_round': 17, 'selection_seed_commit': base, 'selection_seed_tree': tree,
    'current_production_commit': current['production_merge_commit'], 'current_production_tree': tree,
    'parents': selected['parents'], 'hypothesis': selected['hypothesis'], 'selection': policy,
    'knowledge_map_sha256': digest(INSTANCE / 'map.json'), 'paper_reading_destination': ALPHA,
    'traffic_status': 'Not measured; no analytics added, traffic uplift is not inferred from search eval',
    'unchanged_vs_seed': ['All bytes except nine exact URL/label replacements', 'R17 method blocks and R16 H2s',
        'R9 result data', 'arXiv scholarly identifiers, PDF, JSON-LD sameAs, CITATION.cff and BibTeX',
        'canonical project URLs and all project links', 'script.js', 'styles.css', 'map', 'queries', 'judge', 'engine settings'],
    'deployment_plan': 'Require separate R18 approval. Starting from then-current main, apply exact R17-based candidate; reconcile teammate changes and verify full tree plus all seven served changed resources before/after collection.'})
cli('scan', '--no-interactive', name='wrapper-scan.txt')
cli('configure', '--part', 'index.html', '--metric', 'live_project_citation_rate', '--metric-goal', 'maximize',
    '--metric-command', f'python3 {ROOT / "outer_metric.py"}', '--mode', 'sequential', '--rounds', '1',
    '--metric-timeout', '120', '--no-interactive', name='wrapper-configure.txt')
run = json.loads(cli('run', '--part', 'index.html', '--no-interactive', '--json', name='wrapper-run.json'))
pool.update({'current_round': 18, 'selected_candidate_id': SELECTED, 'policy': policy,
             'updated_at': dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')})
assert pool['best_observed'] == best
write('candidate-pool-selected.json', pool)
assert digest(pool_path) == old_hash
pool_path.write_text(json.dumps(pool, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({'run': run, 'selected': SELECTED, 'seed_round': 17, 'old_proposals_preserved': 11,
    'history_count': 18, 'operations': 9, 'files': FILES, 'inner_score': 'not computed'}, indent=2))
