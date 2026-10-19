"""Prepare two factual reference-page H1s on best R18; live R19 stays untouched."""
import copy
import datetime as dt
import re
import shutil
from common import *
from geo_eval.discovery import URL_RE

assert os.environ.get('SLURM_JOB_ID')
assert not ROOT.joinpath('wrapper-run.json').exists(), 'Do not initialize twice'
pool_path = INSTANCE / 'candidate-pool.json'
old_hash = digest(pool_path)
pool = json.loads(pool_path.read_text())
assert pool['current_round'] == 19 and {h['id'] for h in pool['history']} == {f'r{i}' for i in range(20)}
assert len(pool['proposals']) == 13 and SELECTED not in {p['id'] for p in pool['proposals']}
best = copy.deepcopy(pool['best_observed'])
assert best['round'] == 18 and best['decision'] == 'keep' and best['outer_observation']['project_citations'] == 12
base_round = INSTANCE / 'runs/round-18-alphaxiv-paper-routing'
previous = INSTANCE / 'runs/round-19-shared-entity-combination'
control_live,latest = base_round / 'r18-live',previous / 'r19-live'
control = json.loads(control_live.joinpath('summary.json').read_text())
recent = json.loads(latest.joinpath('summary.json').read_text())
assert json.loads(control_live.joinpath('audit.json').read_text())['passed']
assert json.loads(latest.joinpath('audit.json').read_text())['passed']
assert control['scheduled'] == best['outer_observation'] and control['scheduled']['valid_responses'] == 60
assert recent['scheduled']['valid_responses'] == 60 and recent['scheduled']['project_citations'] == 12 and recent['decision'] == 'discard'
base,tree = best['candidate_commit'],best['candidate_tree']
assert base == 'dda361dcd45f2eee5cff5402a3d8b8a5421ddd33' and tree == 'ad41cd32f93433b1be065fc8d1969d8da78f2600'
assert git(SITE,'rev-parse','HEAD') == base and git(SITE,'rev-parse','HEAD^{tree}') == tree
assert not git(SITE,'status','--porcelain') and not git(PRODUCTION,'status','--porcelain')
production_commit,production_tree = git(PRODUCTION,'rev-parse','HEAD'),git(PRODUCTION,'rev-parse','HEAD^{tree}')
assert production_commit == recent['production_merge_commit'] == 'ab6847afc14de3a9067361b071605de711c96337'
assert production_tree == recent['production_tree'] == '12b28c84303366ae8e4117709ec0166c1919ae9a'
assert git(SITE,'diff','--name-only',base,production_commit).splitlines() == HTML
prior_ops = json.loads(previous.joinpath('operations.json').read_text())['operations']
assert len(prior_ops) == 4
for name,op in zip(HTML,prior_ops):
    current = PRODUCTION.joinpath(name).read_text()
    assert current.count(op['after']) == 1
    assert current.replace(op['after'],op['before'],1) == SITE.joinpath(name).read_text()
    assert ROOT.joinpath('served-r19',name).read_bytes() == PRODUCTION.joinpath(name).read_bytes()
write('candidate-pool-before.json',pool)
ROOT.joinpath('sources').mkdir(exist_ok=True)
source_round = INSTANCE / 'runs/round-16-descriptive-section-headings'
for source,target in [(source_round / 'operations.json','r16-operations.json'),(previous / 'operations.json','r19-operations.json'),(base_round / 'operations.json','r18-operations.json')]:
    shutil.copy2(source,ROOT / 'sources' / target)
heading_source = json.loads(ROOT.joinpath('sources/r16-operations.json').read_text())['operations'][0]['after']
inner = re.search(r'<h2[^>]*>(.*?)</h2>',heading_source,re.S)[1]
assert inner == 'How EAU adapts<br><em>the training system.</em>'
assert heading_source in SITE.joinpath('index.html').read_text()
assert 'an adaptive training system' in SITE.joinpath('research-context.html').read_text()
operations = [
    {'op':'replace_text','node':'file:method.html','before':'<h1>What does EAU<br><em>adapt?</em></h1>',
     'after':'<h1>' + inner + '</h1>'},
    {'op':'replace_text','node':'file:research-context.html','before':'<h1>Where does EAU<br><em>fit?</em></h1>',
     'after':'<h1>EAU as an<br><em>adaptive training system.</em></h1>'}]
assert all(SITE.joinpath(op['node'][5:]).read_text().count(op['before']) == 1 for op in operations)
write('operations.json',{'operations':operations})
write('manual-operations.json',{'operations':operations,'reason':'Both HTML files are linked asset nodes with content fingerprints but no replace_text support in the current graph. Apply the two exact replacements with apply_patch in the allocated worktree; no core extension.'})
write('wording-source.json',{'seed_round':18,'parents':['r18'],
    'method_heading':{'source_file':'index.html','source_round':16,'source_operation':'sources/r16-operations.json','source_html':heading_source,'new_h1':operations[0]['after'],
        'interpretation':'Reuse visible wording only on a different page and heading level, not replay of the R16 homepage operation or inheritance of its score.'},
    'context_heading':{'source_file':'research-context.html','source_phrase':'an adaptive training system','new_h1':operations[1]['after'],'claim':'Existing lead already describes EAU this way; no new mechanism or performance claim.'},
    'source_sha256':{p.name:digest(p) for p in sorted(ROOT.joinpath('sources').iterdir())}})
selected = {'id':SELECTED,'status':'selected_preparing','measured':False,'round':20,'change_id':CHANGE_ID,
    'parents':['r18'],'retain_for_combinations':True,'files':FILES,'base_commit':base,
    'modules':['method-reference','research-context','reference-pages','presentation'],
    'hypothesis':'Test two topical, entity-naming H1 headings on the method/context entry pages that actually appeared for fuzzy queries, without changing their explanatory paragraphs.',
    'reason_selected':'R19 metadata-only retest tied the twelve R18 citation cells; both fuzzy entry pages remain visible. Test a separate visible-heading bundle instead of assuming a schema lift.',
    'scope':'Exactly two H1 replacements on R18; no other text, facts, links, metadata, schema, scripts or styles differ from the selection seed.',
    'module_dependencies':['method H1 reuses existing R16 framework H2 wording','context H1 uses existing lead terminology','all R18 alphaXiv routes retained','R19 schema bundle deliberately not inherited'],
    'interpretation':'Unmeasured two-heading bundle, not a predicted gain. R16/R18/R19 observations are not added or treated as isolated module effects.'}
pool['proposals'].append(selected)
write('new-proposals.json',[selected])

ROOT.joinpath('control').mkdir(exist_ok=True)
for name in ['summary.json','search-matrix.csv','search-map.json']:
    shutil.copy2(control_live / name,ROOT / 'control' / name)
for name in ['outer_metric.py','queries.txt','search-map.json']:
    shutil.copy2(base_round / name,ROOT / name)
shutil.copy2(control_live / 'collection-settings.json',ROOT / 'collection-settings.json')
assert digest(ROOT / 'queries.txt') == 'f2440c27b9fa7596e902b5bc30a30130e10789564a75f661338742d40876d8ce'
assert digest(ROOT / 'control/search-matrix.csv') == 'f4c13a905941353d775de225ba6b2e38b2525f1f9116fee2bdaafb85a250a2a4'
registry = json.loads(base_round.joinpath('outer-measurements.json').read_text())
matches = [r for r in registry['measurements'] if r['deployed_tree'] == tree]
assert len(matches) == 1 and matches[0]['label'] == 'r18-immediate-live'
control_record = copy.deepcopy(matches[0])
control_record.update({'label':'r18-best-reused-control','source_label':'r18-immediate-live','matrix':'control/search-matrix.csv','measured_at':control['measured_at'],
    'verification':'Exact R18 tree and original complete 12/60 observation, not the tied but distinct R19 matrix; historical control, no new R20 searches'})
write('outer-measurements.json',{'measurements':[control_record]})
write('production-context.json',{'production_commit':production_commit,'production_tree':production_tree,'production_round':19,'production_observation':recent['scheduled'],
    'selection_seed_round':18,'selection_seed_commit':base,'selection_seed_tree':tree,'seed_observation':control['scheduled'],'best_observed_before':best,
    'seed_differs_from_production':True,'difference_verified':'Only the four exact archived R19 JSON-LD replacements; reversing them recovers the R18 seed files exactly.',
    'baseline_choice':'R18 wins the strict tie rule; R19 12/60 is preserved as latest evidence, not relabelled as the R18 baseline.',
    'production_unchanged':True,'requires_separate_publication_approval':True})
policy = copy.deepcopy(pool['policy'])
policy.update({'baseline':'Best complete R18: 12/60, primary 20.0, composite 35.19444; original historical matrix, not R19 or a fresh simultaneous control. Keep requires strictly more than 12/60 and all 60 valid.',
    'current_production':'R19 unchanged, 12/60 discard (tie); R20 seed is best R18, all user-required alphaXiv routes retained',
    'deployment':'Separate explicit R20 approval required. Candidate differs from current production in four HTML files: remove the unselected R19 schema bundle plus two visible reference H1 changes. Verify complete tree and all four served files before/after real collection.',
    'history':'All twenty R0–R19 observations, thirteen old proposals and best_observed R18 unchanged; new two-heading proposal remains unmeasured. Do not add parent scores.'})
write('outer-only-policy.json',policy)
engine_files = {'gpt-web':'gpt-web-answers.jsonl','codex-search':'codex-answers-complete.jsonl','tavily-search':'tavily-answers.jsonl','exa-search':'exa-answers.jsonl'}
ROOT.joinpath('r19-evidence').mkdir(exist_ok=True)
for name in ['summary.json',*engine_files.values()]:
    shutil.copy2(latest / name,ROOT / 'r19-evidence' / name)
queries = ROOT.joinpath('queries.txt').read_text().splitlines()
answers = {e:{r['query']:r for r in map(json.loads,ROOT.joinpath('r19-evidence',name).read_text().splitlines())} for e,name in engine_files.items()}
assert all(len(rows) == 15 and set(rows) == set(queries) and all(r['status'] == 'ok' for r in rows.values()) for rows in answers.values())
write('r19-search-evidence.json',{'tool':'Saved actual complete R19 four-engine answers; not new R20 probes','result_scope':'Displayed source URLs only, not top-ten ranks, costs, traffic or predicted heading lift',
    'observations':[{'query_id':f'Q{i:02d}','result_urls':list(dict.fromkeys(u.rstrip('.,;:!?*_') for e in engine_files for u in URL_RE.findall(answers[e][q]['text']))),
        'raw_file':'r19-evidence/gpt-web-answers.jsonl','raw_files':{e:'r19-evidence/' + name for e,name in engine_files.items()}} for i,q in enumerate(queries,1)]})
support = [r for r in json.loads(latest.joinpath('explicit-project-urls.json').read_text()) if any(re.search(r'/(method|paper|research-context)\.html',u) for u in r['urls'])]
assert len(support) == 5
write('observed-entry-surfaces.json',{'source_round':19,'cells':support,'focus':'The one method and one context source-URL cell for fuzzy queries; paper identity H1 already explicit and left unchanged.',
    'selection_limit':'Source visibility motivates a test; it does not establish that headings or any prior module caused these citations.'})
actions = {'homepage-identity':'Keep R18 home H1, R16 H2s and R17 static method unchanged; do not replay failed R12 H1',
    'method-reference':'Replace question H1 with exact existing framework heading wording; all paragraphs and evidence unchanged',
    'research-context':'Replace question H1 with the existing adaptive-training-system description; scope/evidence boundaries unchanged',
    'paper-authority':'Keep R18 paper record, author/year/citation data and paper H1 unchanged; no R19 shared schema inheritance',
    'machine-readable-summary':'Keep llms.txt and alphaXiv Paper entry unchanged',
    'repository-authority':'Keep README and alphaXiv Paper entry unchanged; no external repository changes',
    'crawler-routing':'Keep robots/sitemap; no claim of indexed new bytes or inferred graph reach',
    'presentation':'Reuse existing H1/br/em markup and styles; no CSS/JS/layout rewrite, rendered wrapping untested',
    'reference-pages':'Test two visible entry H1s together; R8 routes and all outgoing destinations retained',
    'external-paper-entry':'Keep alphaXiv click routes; external backlink state unknown and author-owned pages untouched'}
assert set(actions) == {m['id'] for m in pool['modules']}
write('module-review.json',{'basis':'Best R18 control plus complete R19 tie and returned source URLs; no new R20 searches',
    'latest_observation':{'round':19,'project_citations':12,'explicit_project_url_cells':11,'explicit_support_page_url_cells':5,'fuzzy_citations':2,'broad_citations':1,'decision':'discard'},
    'reviews':[{'module':k,'action':v} for k,v in actions.items()],
    'alternatives_retained':[{'id':p['id'],'status':p['status'],'measured':p.get('measured',False),'action':'Retain unchanged; no silent bundling or score addition'} for p in pool['proposals'] if p['id'] != SELECTED],
    'selection_limit':'R19 immediate tie does not prove the metadata has no later effect; R16 homepage heading result does not predict support-page H1 lift.'})
config = json.loads(previous.joinpath('config.json').read_text())
config['interventions'][0] = {'id':CHANGE_ID,'candidate_id':CHANGE_ID,'nodes':['file:method.html','file:research-context.html'],'manual_files':FILES,
    'graph_scope':'Both are content-hashed linked assets but have no text mutation operation; apply_patch two exact H1s, no wrapper-core change.',
    'source_url':'https://eau-meta-agent.github.io/method.html','link_state':'present','link_evidence_url':'https://eau-meta-agent.github.io/method.html',
    'change_kind':'node','local_state':'R19 returns method/context source URLs for two fuzzy queries; visible H1s are questions rather than topical statements.',
    'hypothesis':selected['hypothesis'],'candidate_arms':[{'id':p['id'],'status':p['status'],'hypothesis':p['hypothesis']} for p in pool['proposals']]}
config['interventions'][1]['hypothesis'] = 'External paper edits still need separate author authority and are outside R20'
write('config.json',config)
write('change.json',{'round':20,'change_id':CHANGE_ID,'pool_candidate_id':SELECTED,'state':'preparing','part':PART,'files':FILES,
    'graph_nodes':config['interventions'][0]['nodes'],'manual_files':FILES,'selection_seed_round':18,'selection_seed_commit':base,'selection_seed_tree':tree,
    'current_production_commit':production_commit,'current_production_tree':production_tree,'current_production_round':19,'parents':['r18'],
    'hypothesis':selected['hypothesis'],'selection':policy,'knowledge_map_sha256':digest(INSTANCE / 'map.json'),
    'unchanged_vs_seed':['All bytes except two H1 replacements','all HTML head metadata/JSON-LD','homepage, paper page, paragraphs, benchmark data and citations',
        'all R18 alphaXiv links/config/README/llms','scripts/styles/assets/crawler files','map/queries/judge/normalizer/engine settings'],
    'planned_scope_vs_current_production':HTML,'production_difference':'Restore R18 metadata in four HTML pages, then replace two reference H1s; do not deploy the R19 discarded schema experiment.',
    'deployment_plan':'Separate R20 approval required. Recheck then-current main and reconcile teammate changes, apply the complete R18-based candidate, verify full tree and all four changed served files before/after the frozen 60 real requests.'})
cli('scan','--no-interactive',name='wrapper-scan.txt')
cli('configure','--part',PART,'--metric','live_project_citation_rate','--metric-goal','maximize','--metric-command',f'python3 {ROOT / "outer_metric.py"}',
    '--mode','sequential','--rounds','1','--metric-timeout','120','--no-interactive',name='wrapper-configure.txt')
run = json.loads(cli('run','--part',PART,'--no-interactive','--json',name='wrapper-run.json'))
pool.update({'current_round':20,'selected_candidate_id':SELECTED,'policy':policy,'updated_at':dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')})
assert pool['best_observed'] == best and digest(pool_path) == old_hash
write('candidate-pool-selected.json',pool)
pool_path.write_text(json.dumps(pool,ensure_ascii=False,indent=2) + '\n')
print(json.dumps({'run':run,'selected':SELECTED,'seed_round':18,'production_round':19,'old_proposals_preserved':13,'history_count':20,
    'heading_operations':2,'inner_score':'not computed'},indent=2))
