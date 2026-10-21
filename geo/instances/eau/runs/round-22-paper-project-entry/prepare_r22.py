"""Review all modules/candidates; select one existing paper-link relocation."""
import copy
import datetime as dt
import shutil
from common import *
from geo_eval.discovery import URL_RE

assert os.environ.get('SLURM_JOB_ID')
assert not ROOT.joinpath('wrapper-run.json').exists(), 'Do not initialize twice'
pool_path = INSTANCE / 'candidate-pool.json'
old_hash = digest(pool_path)
pool = json.loads(pool_path.read_text())
assert pool['current_round'] == 21 and len(pool['history']) == 22 and len(pool['proposals']) == 15
assert {h['id'] for h in pool['history']} == {f'r{i}' for i in range(22)}
assert SELECTED not in {p['id'] for p in pool['proposals']}
best = copy.deepcopy(pool['best_observed'])
assert best['round'] == 18 and best['outer_observation']['project_citations'] == 12
base_round = INSTANCE / 'runs/round-18-alphaxiv-paper-routing'
previous = INSTANCE / 'runs/round-21-descriptive-static-evidence-combination'
control_live,latest = base_round / 'r18-live',previous / 'r21-live'
control,recent = [json.loads(p.joinpath('summary.json').read_text()) for p in [control_live,latest]]
assert control['scheduled'] == best['outer_observation'] and control['scheduled']['valid_responses'] == 60
assert recent['scheduled']['valid_responses'] == 60 and recent['scheduled']['project_citations'] == 12 and recent['decision'] == 'discard'
assert all(json.loads(p.joinpath('audit.json').read_text())['passed'] for p in [control_live,latest])
assert json.loads(latest.joinpath('wrapper-status.json').read_text())['runs']['20261020T055744Z-index-html']['status'] == 'completed'
base,tree = best['candidate_commit'],best['candidate_tree']
assert git(SITE,'rev-parse','HEAD') == base == 'dda361dcd45f2eee5cff5402a3d8b8a5421ddd33'
assert git(SITE,'rev-parse','HEAD^{tree}') == tree == 'ad41cd32f93433b1be065fc8d1969d8da78f2600'
assert not git(SITE,'status','--porcelain') and not git(PRODUCTION,'status','--porcelain')
production_commit,production_tree = git(PRODUCTION,'rev-parse','HEAD'),git(PRODUCTION,'rev-parse','HEAD^{tree}')
assert production_commit == recent['production_merge_commit'] == '3f0c8143e9e23eb351e1727425ce1ed05606d4ec'
assert production_tree == recent['production_tree'] == '49c3d78bb28cbadbcfa7dc78673b8a104f640084'
assert git(SITE,'diff',base,production_commit,'--name-only').splitlines() == ['index.html']
table_op = json.loads(previous.joinpath('operations.json').read_text())['operations'][0]
assert SITE.joinpath('index.html').read_text().replace(table_op['before'],table_op['after'],1) == PRODUCTION.joinpath('index.html').read_text()
assert all(ROOT.joinpath('served-r21',n).read_bytes() == PRODUCTION.joinpath(n).read_bytes() for n in HTML)
write('candidate-pool-before.json',pool)
ROOT.joinpath('parents').mkdir()
for src,name in [(base_round / 'operations.json','r18-operations.json'),(previous / 'operations.json','r21-operations.json'),(previous / 'change.json','r21-change.json'),(latest / 'summary.json','r21-live-summary.json')]:
    shutil.copy2(src,ROOT / 'parents' / name)
link = '<p>Official project site: <a class="text-link" href="https://eau-meta-agent.github.io/">eau-meta-agent.github.io</a>.</p>'
anchor = 'Evaluation covers UserGym, ColBench, and τ²-bench with Qwen3-4B and Qwen2.5-7B-Instruct.</p>'
paper = SITE.joinpath('paper.html').read_text()
assert paper.count(link) == paper.count(anchor) == 1 and '\n    ' + link + '\n' in paper
write('edit-plan.json',{'node':'file:paper.html','method':'Main-agent apply_patch in allocated candidate; asset node exposes no geo-apply text operations',
    'semantic_change':'Move the single existing official-project paragraph from the reference footer to the identity overview-copy, immediately after the existing evaluation sentence',
    'link_paragraph':link,'identity_anchor':anchor,'footer_before':'\n    ' + link + '\n','footer_after':'\n',
    'identity_before':anchor,'identity_after':anchor + '\n    ' + link,
    'new_text':False,'new_link':False,'new_claim':False,'wrapper_core_changed':False})
selected = {'id':SELECTED,'status':'selected_preparing','measured':False,'round':22,'change_id':CHANGE_ID,
    'parents':['r18'],'retain_for_combinations':True,'files':FILES,'base_commit':base,
    'modules':['paper-authority','homepage-identity','reference-pages'],
    'hypothesis':'Placing the already-present official project link next to the bibliographic identity may make the existing source-to-project route easier to extract; test a relocation, not an absent-edge repair.',
    'reason_selected':'R19/R20/R21 tied best R18. Three R21 Exa cells explicitly returned paper.html; its identity/results snippets omit the official-project paragraph currently in the footer. This is a bounded entry-surface test, not evidence of a causal omission or predicted lift.',
    'scope':'Move exactly one existing paragraph inside paper.html; no wording, href, link count, head, data, styles, scripts or other seed file changes.',
    'module_dependencies':['Existing R8 official project reference route retained in R18','R18 paper identity and alphaXiv reading route','Unchanged R18 homepage and result/method evidence'],
    'interpretation':'A new single-relocation candidate on R18, not a R21 continuation tree. Old scores and decisions remain unchanged; no parent scores are added.'}
pool['proposals'].append(selected)
write('new-proposals.json',[selected])
ROOT.joinpath('control').mkdir()
for name in ['summary.json','search-matrix.csv','search-map.json']:
    shutil.copy2(control_live / name,ROOT / 'control' / name)
for name in ['outer_metric.py','queries.txt','search-map.json']:
    shutil.copy2(base_round / name,ROOT / name)
shutil.copy2(control_live / 'collection-settings.json',ROOT / 'collection-settings.json')
assert digest(ROOT / 'control/search-matrix.csv') == 'f4c13a905941353d775de225ba6b2e38b2525f1f9116fee2bdaafb85a250a2a4'
registry = json.loads(base_round.joinpath('outer-measurements.json').read_text())
match = [r for r in registry['measurements'] if r['deployed_tree'] == tree]
assert len(match) == 1 and match[0]['label'] == 'r18-immediate-live'
r = copy.deepcopy(match[0])
r.update({'label':'r18-best-reused-control','source_label':'r18-immediate-live','matrix':'control/search-matrix.csv',
    'measured_at':control['measured_at'],'verification':'Original R18 complete historical observation, not R21 or a fresh control; no R22 probes yet'})
write('outer-measurements.json',{'measurements':[r]})
write('production-context.json',{'production_round':21,'production_commit':production_commit,'production_tree':production_tree,'production_observation':recent['scheduled'],
    'selection_seed_round':18,'selection_seed_commit':base,'selection_seed_tree':tree,'seed_observation':control['scheduled'],
    'seed_differs_from_production':True,'difference_verified':'Current R21 differs from best R18 only by the exact retained R14 homepage table insertion',
    'baseline_choice':'Strict primary tie retains R18; R21 report-only composite 35.88889 and fuzzy gain do not promote it',
    'production_unchanged':True,'requires_separate_publication_approval':True})
policy = copy.deepcopy(pool['policy'])
policy.update({'baseline':'Best R18 original complete historical matrix: 12/60, primary 20.0, composite 35.19444; keep requires all 60 valid and strictly more than 12/60; ties discard.',
    'current_production':'R21 unchanged, 12/60 discard; unpublished R22 starts from R18 and retains alphaXiv routes',
    'deployment':'Separate R22 approval required. Future diff versus R21 spans index/paper: remove the unkept R21 table and relocate the existing paper-page project link. Verify full tree and BOTH changed served pages before/after collection.',
    'history':'All twenty-two R0–R21 observations, fifteen older proposals and best R18 unchanged; the sixteenth proposal is unmeasured. Never add parent scores.'})
write('outer-only-policy.json',policy)
engine_files = {'gpt-web':'gpt-web-answers.jsonl','codex-search':'codex-answers-complete.jsonl','tavily-search':'tavily-answers.jsonl','exa-search':'exa-answers.jsonl'}
queries = ROOT.joinpath('queries.txt').read_text().splitlines()
answers = {e:{r['query']:r for r in map(json.loads,latest.joinpath(n).read_text().splitlines())} for e,n in engine_files.items()}
assert len(queries) == 15 and all(len(rows) == 15 and set(rows) == set(queries) and all(r['status'] == 'ok' for r in rows.values()) for rows in answers.values())
write('r21-search-evidence.json',{'tool':'Saved actual complete R21 four-engine response source URLs; no new R22 probes',
    'result_scope':'Displayed source URLs only, not inferred rank, indexing, traffic or candidate lift',
    'observations':[{'query_id':f'Q{i:02d}','result_urls':list(dict.fromkeys(u.rstrip('.,;:!?*_') for e in engine_files for u in URL_RE.findall(answers[e][q]['text']))),
        'raw_file':'../round-21-descriptive-static-evidence-combination/r21-live/gpt-web-answers.jsonl',
        'raw_files':{e:'../round-21-descriptive-static-evidence-combination/r21-live/' + n for e,n in engine_files.items()}} for i,q in enumerate(queries,1)]})
urls = json.loads(latest.joinpath('explicit-project-urls.json').read_text())
paper_cells = [row for row in urls if 'https://eau-meta-agent.github.io/paper.html' in row['urls']]
assert len(paper_cells) == 3 and all(row['engine'] == 'exa-search' for row in paper_cells)
snippets = []
for row in paper_cells:
    text = answers[row['engine']][row['query']]['text']
    pos = text.index('https://eau-meta-agent.github.io/paper.html')
    start = text.rfind('\n\n',0,pos)
    snippet = text[start + 2:pos]
    assert snippet and 'Official project site:' not in snippet
    snippets.append({'query':row['query'],'engine':row['engine'],'source_url':'https://eau-meta-agent.github.io/paper.html','displayed_preceding_snippet':snippet})
write('observed-entry-surfaces.json',{'source_round':21,'paper_url_cells':paper_cells,'paper_url_cell_count':3,'paper_snippets':snippets,
    'existing_link_state':'present, independently verified in served-r21/paper.html footer; do not label it missing',
    'primary_tier_counts':{'exact':8,'fuzzy':3,'broad':1},
    'limit':'Snippet omission motivates placement test only; no evidence of retrieval cause, indexing completeness or future lift'})
actions = {'homepage-identity':'Keep exact R18 home; do not inherit R21 second-backbone table despite fuzzy gain',
    'method-reference':'Keep R17 static method and all R18 method page bytes; no new H1 or schema bundle',
    'research-context':'Keep complete R18 context and evidence boundaries',
    'paper-authority':'Relocate one existing canonical project paragraph into visible identity copy; preserve wording, href, metadata, authors and reported numbers',
    'machine-readable-summary':'Keep R18 llms and alphaXiv route unchanged',
    'repository-authority':'Keep R18 README unchanged',
    'crawler-routing':'Keep robots/sitemap; no speculative indexing change',
    'presentation':'Keep all CSS/JS/assets and existing paragraph/link classes; no browser layout claim',
    'reference-pages':'Keep all page paths and total link counts; paper footer retains its three support links',
    'external-paper-entry':'External link state remains unknown and author-owned pages untouched; alphaXiv paper reading routes retained'}
assert set(actions) == {m['id'] for m in pool['modules']}
write('module-review.json',{'basis':'Best R18, complete R21 tie, three actual paper-page Exa URLs and archived snippets; no new paid probes',
    'reviews':[{'module':k,'action':v} for k,v in actions.items()],
    'alternatives_retained':[{'id':p['id'],'status':p['status'],'measured':p.get('measured'),
        'action':'Retain original discard and fuzzy gain/exact loss; no inheritance based on secondary score' if p['id'] == 'descriptive-static-evidence-combination' else 'Retain unchanged for future combinations; no implicit replay or score addition'} for p in pool['proposals'] if p['id'] != SELECTED],
    'selection_limit':'Three primary ties do not establish no long-term effect. This test changes placement only on the current best tree; real strict improvement remains required.'})
config = json.loads(previous.joinpath('config.json').read_text())
config['interventions'][0] = {'id':CHANGE_ID,'candidate_id':CHANGE_ID,'nodes':['file:paper.html'],
    'source_url':'https://eau-meta-agent.github.io/paper.html','link_state':'present','link_evidence_url':'https://eau-meta-agent.github.io/paper.html',
    'change_kind':'node','local_state':'Three R21 Exa cells return the existing paper page; its official project link is already present in the footer, not in returned identity/results snippets',
    'hypothesis':selected['hypothesis'],'candidate_arms':[{'id':p['id'],'status':p['status'],'hypothesis':p['hypothesis']} for p in pool['proposals']]}
config['interventions'][1]['hypothesis'] = 'External paper edits need separate author authority and are outside R22'
write('config.json',config)
write('change.json',{'round':22,'change_id':CHANGE_ID,'pool_candidate_id':SELECTED,'state':'preparing','part':PART,'files':FILES,
    'graph_nodes':['file:paper.html'],'selection_seed_round':18,'selection_seed_commit':base,'selection_seed_tree':tree,
    'current_production_round':21,'current_production_commit':production_commit,'current_production_tree':production_tree,'parents':['r18'],
    'hypothesis':selected['hypothesis'],'selection':policy,'knowledge_map_sha256':digest(INSTANCE / 'map.json'),
    'unchanged_vs_seed':['All paper content except exact paragraph placement','all paper head metadata/schema/results and alphaXiv links',
        'all other website bytes, including R16 H2s, R17 static method, R18 alphaXiv routes','map/query/judge/normalizer/settings'],
    'planned_scope_vs_current_production':DEPLOY_FILES,'production_difference':'Restore best R18 homepage by removing unkept R21 table; relocate one existing paper paragraph, no other production change',
    'deployment_plan':'Separate R22 approval required; recheck then-current main and teammate changes, deploy exact complete tree, verify both index/paper served bytes before/after sixty frozen real requests'})
cli('scan','--no-interactive',name='wrapper-scan.txt')
cli('configure','--part',PART,'--metric','live_project_citation_rate','--metric-goal','maximize','--metric-command',f'python3 {ROOT / "outer_metric.py"}',
    '--mode','sequential','--rounds','1','--metric-timeout','120','--no-interactive',name='wrapper-configure.txt')
run = json.loads(cli('run','--part',PART,'--no-interactive','--json',name='wrapper-run.json'))
pool.update({'current_round':22,'selected_candidate_id':SELECTED,'policy':policy,'updated_at':dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')})
assert pool['best_observed'] == best and digest(pool_path) == old_hash
write('candidate-pool-selected.json',pool)
pool_path.write_text(json.dumps(pool,ensure_ascii=False,indent=2) + '\n')
print(json.dumps({'run':run,'selected':SELECTED,'old_proposals_preserved':15,'history_count':22,'inner_score':'not computed'},indent=2))
