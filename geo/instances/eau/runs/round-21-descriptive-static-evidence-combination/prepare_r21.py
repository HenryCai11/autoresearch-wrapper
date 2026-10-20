"""Select the retained R14 table on best R18; keep live R20 and old scores intact."""
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
assert pool['current_round'] == 20 and len(pool['history']) == 21 and len(pool['proposals']) == 14
assert {h['id'] for h in pool['history']} == {f'r{i}' for i in range(21)}
assert SELECTED not in {p['id'] for p in pool['proposals']}
best = copy.deepcopy(pool['best_observed'])
assert best['round'] == 18 and best['outer_observation']['project_citations'] == 12
base_round = INSTANCE / 'runs/round-18-alphaxiv-paper-routing'
previous = INSTANCE / 'runs/round-20-descriptive-reference-headings'
parent = INSTANCE / 'runs/round-14-static-second-backbone-evidence'
control_live,latest = base_round / 'r18-live',previous / 'r20-live'
control,recent = [json.loads(p.joinpath('summary.json').read_text()) for p in [control_live,latest]]
assert control['scheduled'] == best['outer_observation'] and control['scheduled']['valid_responses'] == 60
assert recent['scheduled']['valid_responses'] == 60 and recent['scheduled']['project_citations'] == 12 and recent['decision'] == 'discard'
assert all(json.loads(p.joinpath('audit.json').read_text())['passed'] for p in [control_live,latest,parent / 'r14-live'])
assert json.loads(previous.joinpath('r20-live/wrapper-status.json').read_text())['runs']['20261019T171243Z-method-html']['status'] == 'completed'
base,tree = best['candidate_commit'],best['candidate_tree']
assert git(SITE,'rev-parse','HEAD') == base == 'dda361dcd45f2eee5cff5402a3d8b8a5421ddd33'
assert git(SITE,'rev-parse','HEAD^{tree}') == tree == 'ad41cd32f93433b1be065fc8d1969d8da78f2600'
assert not git(SITE,'status','--porcelain') and not git(PRODUCTION,'status','--porcelain')
production_commit,production_tree = git(PRODUCTION,'rev-parse','HEAD'),git(PRODUCTION,'rev-parse','HEAD^{tree}')
assert production_commit == recent['production_merge_commit'] == '27f252b85a6e9c3ff83d5ff815f6a704e3db51bc'
assert production_tree == recent['production_tree'] == '8261df22ebbcfa2edc6031f32e2fb51214822ad3'
assert git(SITE,'diff',base,production_commit,'--name-only').splitlines() == ['method.html','research-context.html']
for op in json.loads(previous.joinpath('operations.json').read_text())['operations']:
    name = op['node'][5:]
    text = PRODUCTION.joinpath(name).read_text()
    assert text.count(op['after']) == 1 and text.replace(op['after'],op['before'],1) == SITE.joinpath(name).read_text()
assert all(ROOT.joinpath('served-r20',n).read_bytes() == PRODUCTION.joinpath(n).read_bytes() for n in HTML)
write('candidate-pool-before.json',pool)
ROOT.joinpath('parents').mkdir()
sources = [(parent / 'operations.json','r14-operations.json'),(parent / 'static-second-backbone-source.json','r14-static-second-backbone-source.json'),
    (parent / 'change.json','r14-change.json'),(parent / 'r14-live/summary.json','r14-live-summary.json'),
    (previous / 'operations.json','r20-operations.json'),(base_round / 'operations.json','r18-operations.json'),
    (INSTANCE / 'runs/round-16-descriptive-section-headings/operations.json','r16-operations.json')]
for src,name in sources:
    shutil.copy2(src,ROOT / 'parents' / name)
operations = json.loads(ROOT.joinpath('parents/r14-operations.json').read_text())
assert len(operations['operations']) == 1
op = operations['operations'][0]
assert op['node'] == 'file:index.html' and op['op'] == 'replace_text'
parent_change = json.loads(ROOT.joinpath('parents/r14-change.json').read_text())
parent_summary = json.loads(ROOT.joinpath('parents/r14-live-summary.json').read_text())
assert parent_summary['decision'] == 'discard' and parent_summary['scheduled']['project_citations'] == 5
assert git(SITE,'show',parent_change['candidate_commit'] + ':index.html').count(op['after']) == 1
parent_input = git(SITE,'show',parent_change['selection_seed_commit'] + ':index.html')
assert parent_input.count(op['before']) == 1 and parent_input.replace(op['before'],op['after'],1) == git(SITE,'show',parent_change['candidate_commit'] + ':index.html')
source = json.loads(ROOT.joinpath('parents/r14-static-second-backbone-source.json').read_text())
assert source['source_sha256'] == digest(SITE / 'script.js') and op['after'] == source['rendered_html'] + op['before']
assert SITE.joinpath('index.html').read_text().count(op['before']) == 1 and source['rendered_html'] not in SITE.joinpath('index.html').read_text()
shutil.copy2(ROOT / 'parents/r14-operations.json',ROOT / 'operations.json')
write('combination-source.json',{'parents':['r18','r14'],'base_round':18,'parent_round':14,
    'parent_candidate_commit':parent_change['candidate_commit'],'parent_old_citations':5,'parent_old_decision':'discard',
    'exact_replay':'The exact final R14 one-insertion manifest reproduces its measured candidate from its old seed; replay it on R18 without adding parent scores.',
    'not_r15_replay':'R15 bundled the R12 H1, R13 components and R14 table on R9 and measured 6/60. R21 retains original H1, R16 H2s, R17 components and R18 alphaXiv routes; only R14 table is newly replayed.',
    'parent_artifact_sha256':{p.name:digest(p) for p in ROOT.joinpath('parents').iterdir()}})
selected = {'id':SELECTED,'status':'selected_preparing','measured':False,'round':21,'change_id':CHANGE_ID,
    'parents':['r18','r14'],'retain_for_combinations':True,'files':FILES,'base_commit':base,
    'modules':['homepage-identity','presentation','method-reference','paper-authority'],
    'hypothesis':'Test the exact retained second-backbone static evidence under the kept descriptive results heading and static method reference on R18; no new numerical results or wording.',
    'reason_selected':'R19 schema and R20 H1 bundles tied the twelve R18 cells; actual R20 homepage URLs remain a visible entry surface, while broad citations are only 1/20. Test one existing evidence-availability bundle, not a predicted gain.',
    'scope':'One exact R14 insertion in the results section of R18 index.html; all original bytes, metadata, labels, headings, links, scripts and styles preserved.',
    'module_dependencies':['R16 descriptive results heading','R17 static component reference','R9 default Qwen3 table and unchanged model switch','R18 alphaXiv routes','R14 separately labelled static Qwen2.5 table'],
    'interpretation':'Separate unmeasured combination; R14 5/60 and R15 6/60 remain discarded original observations, not additive effects. R19/R20 discarded bundles are not silently inherited.'}
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
    'measured_at':control['measured_at'],'verification':'Original R18 complete historical observation, not R20 or a fresh control; no R21 probes yet'})
write('outer-measurements.json',{'measurements':[r]})
write('production-context.json',{'production_round':20,'production_commit':production_commit,'production_tree':production_tree,'production_observation':recent['scheduled'],
    'selection_seed_round':18,'selection_seed_commit':base,'selection_seed_tree':tree,'seed_observation':control['scheduled'],
    'seed_differs_from_production':True,'difference_verified':'Only the two archived R20 H1 operations; reversing them recovers R18 exactly',
    'baseline_choice':'Strict tie rule retains R18; R20 composite 34.83333 is secondary only. Do not relabel the R20 matrix as R18.',
    'production_unchanged':True,'requires_separate_publication_approval':True})
policy = copy.deepcopy(pool['policy'])
policy.update({'baseline':'Best R18 original complete historical matrix: 12/60, primary 20.0, composite 35.19444; keep requires all 60 valid and strictly more than 12/60; ties discard.',
    'current_production':'R20 unchanged, 12/60 discard; R21 is seeded from R18 and retains all alphaXiv routes',
    'deployment':'Separate R21 approval required. Future diff versus live R20 spans index/method/context: add R14 table, restore the two R18 H1s. Verify full tree and all three changed served pages before/after real collection.',
    'history':'All twenty-one R0–R20 observations, fourteen older proposals and best R18 unchanged; new combination is unmeasured. Never add parent scores.'})
write('outer-only-policy.json',policy)
engine_files = {'gpt-web':'gpt-web-answers.jsonl','codex-search':'codex-answers-complete.jsonl','tavily-search':'tavily-answers.jsonl','exa-search':'exa-answers.jsonl'}
queries = ROOT.joinpath('queries.txt').read_text().splitlines()
answers = {e:{r['query']:r for r in map(json.loads,latest.joinpath(n).read_text().splitlines())} for e,n in engine_files.items()}
assert len(queries) == 15 and all(len(rows) == 15 and set(rows) == set(queries) and all(r['status'] == 'ok' for r in rows.values()) for rows in answers.values())
write('r20-search-evidence.json',{'tool':'Saved actual complete R20 four-engine response source URLs; no new R21 probes',
    'result_scope':'Displayed source URLs only, not inferred top-ten rank, indexing, traffic or candidate lift',
    'observations':[{'query_id':f'Q{i:02d}','result_urls':list(dict.fromkeys(u.rstrip('.,;:!?*_') for e in engine_files for u in URL_RE.findall(answers[e][q]['text']))),
        'raw_file':'../round-20-descriptive-reference-headings/r20-live/gpt-web-answers.jsonl',
        'raw_files':{e:'../round-20-descriptive-reference-headings/r20-live/' + n for e,n in engine_files.items()}} for i,q in enumerate(queries,1)]})
urls = json.loads(latest.joinpath('explicit-project-urls.json').read_text())
home = [row for row in urls if 'https://eau-meta-agent.github.io/' in row['urls']]
assert len(home) == 9
write('observed-entry-surfaces.json',{'source_round':20,'homepage_url_cells':home,'homepage_url_cell_count':9,
    'broad_citations':1,'broad_total':20,'fuzzy_citations':2,'fuzzy_total':20,
    'limit':'Observed home entry URLs motivate a test; no evidence that a table, prior headings, or metadata caused a citation or will improve broad retrieval.'})
actions = {'homepage-identity':'Keep original H1 and R16 H2s; add exact R14 evidence only in results, no R12 H1 replay',
    'method-reference':'Keep R17 static component reference and R18 method page; no R20 H1 inheritance',
    'research-context':'Keep complete R18 context page and evidence boundaries',
    'paper-authority':'Keep paper record and scholarly metadata; table numbers cross-checked against existing JS, no new benchmark result',
    'machine-readable-summary':'Keep R18 llms and alphaXiv Paper route unchanged',
    'repository-authority':'Keep R18 README and alphaXiv Paper route unchanged',
    'crawler-routing':'Keep robots and sitemap; no indexed-byte or hypothetical graph-reach claim',
    'presentation':'Reuse R14 semantic default-open details/table with independent IDs and caption; leave switch/default charts/CSS/JS unchanged; rendered layout untested',
    'reference-pages':'Keep all R18 pages/routes; R20 H1 proposal remains separate discarded evidence',
    'external-paper-entry':'Keep alphaXiv reading entry points; external backlink state unknown and author-owned pages untouched'}
assert set(actions) == {m['id'] for m in pool['modules']}
write('module-review.json',{'basis':'Best R18 and complete R20 tie, actual returned home URLs; no R21 paid searches',
    'reviews':[{'module':k,'action':v} for k,v in actions.items()],
    'alternatives_retained':[{'id':p['id'],'status':p['status'],'measured':p.get('measured'),
        'action':'Reuse exact final table as a separately measured combination; original discard unchanged' if p['id'] == 'static-second-backbone-evidence' else 'Retain unchanged; R15 multi-bundle failure is not silently replayed or treated as an isolated table effect' if p['id'] == 'static-entry-combination' else 'Retain unchanged; no silent bundling or score addition'} for p in pool['proposals'] if p['id'] != SELECTED],
    'selection_limit':'Neither historical R14/R15 failures nor later R18 gains identify an isolated contribution. Test the one manifest on the current best tree and keep only real strict improvement.'})
config = json.loads(previous.joinpath('config.json').read_text())
config['interventions'][0] = {'id':CHANGE_ID,'candidate_id':CHANGE_ID,'nodes':['file:index.html','section:results'],
    'source_url':'https://eau-meta-agent.github.io/','link_state':'present','link_evidence_url':'https://eau-meta-agent.github.io/',
    'change_kind':'node','local_state':'R20 returned the home URL in nine exact-query cells; default static results only expose Qwen3 while Qwen2.5 needs the switch',
    'hypothesis':selected['hypothesis'],'candidate_arms':[{'id':p['id'],'status':p['status'],'hypothesis':p['hypothesis']} for p in pool['proposals']]}
config['interventions'][1]['hypothesis'] = 'External paper edits need separate author authority and are outside R21'
write('config.json',config)
write('change.json',{'round':21,'change_id':CHANGE_ID,'pool_candidate_id':SELECTED,'state':'preparing','part':PART,'files':FILES,
    'graph_nodes':['file:index.html','section:results'],'selection_seed_round':18,'selection_seed_commit':base,'selection_seed_tree':tree,
    'current_production_round':20,'current_production_commit':production_commit,'current_production_tree':production_tree,'parents':['r18','r14'],
    'hypothesis':selected['hypothesis'],'selection':policy,'knowledge_map_sha256':digest(INSTANCE / 'map.json'),
    'unchanged_vs_seed':['All original bytes except the exact R14 table insertion','default Qwen3 results and switch','R16 H2s and R17 method reference',
        'heads/schema, paper and reference pages','all R18 alphaXiv routes, scripts/styles/assets/crawler files','map/query/judge/normalizer/settings'],
    'planned_scope_vs_current_production':DEPLOY_FILES,'production_difference':'Add one R14 static table to R18 index; restore R18 method/context H1s instead of inheriting discarded R20 headings',
    'deployment_plan':'Separate R21 approval required; recheck then-current main, reconcile teammate changes, deploy exact complete candidate tree and verify all three changed served files before/after sixty frozen real requests'})
cli('scan','--no-interactive',name='wrapper-scan.txt')
cli('configure','--part',PART,'--metric','live_project_citation_rate','--metric-goal','maximize','--metric-command',f'python3 {ROOT / "outer_metric.py"}',
    '--mode','sequential','--rounds','1','--metric-timeout','120','--no-interactive',name='wrapper-configure.txt')
run = json.loads(cli('run','--part',PART,'--no-interactive','--json',name='wrapper-run.json'))
pool.update({'current_round':21,'selected_candidate_id':SELECTED,'policy':policy,'updated_at':dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')})
assert pool['best_observed'] == best and digest(pool_path) == old_hash
write('candidate-pool-selected.json',pool)
pool_path.write_text(json.dumps(pool,ensure_ascii=False,indent=2) + '\n')
print(json.dumps({'run':run,'selected':SELECTED,'parents':['r18','r14'],'old_proposals_preserved':14,'history_count':21,'operations':1,'inner_score':'not computed'},indent=2))
