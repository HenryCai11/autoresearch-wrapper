"""Replay the final measured R10 schema bundle on exact kept R18, not its draft."""
import copy
import datetime as dt
import re
import shutil
from common import *
from geo_eval.discovery import URL_RE

assert os.environ.get('SLURM_JOB_ID')
assert not ROOT.joinpath('wrapper-run.json').exists(), 'Do not create a second R19 run'
pool_path = INSTANCE / 'candidate-pool.json'
old_hash = digest(pool_path)
pool = json.loads(pool_path.read_text())
assert pool['current_round'] == 18 and {h['id'] for h in pool['history']} == {f'r{i}' for i in range(19)}
assert len(pool['proposals']) == 12 and SELECTED not in {p['id'] for p in pool['proposals']}
best = copy.deepcopy(pool['best_observed'])
assert best['round'] == 18 and best['decision'] == 'keep' and best['outer_observation']['project_citations'] == 12
previous = INSTANCE / 'runs/round-18-alphaxiv-paper-routing'
live = INSTANCE / best['artifact_dir']
summary = json.loads(live.joinpath('summary.json').read_text())
assert json.loads(live.joinpath('audit.json').read_text())['passed']
assert summary['scheduled'] == best['outer_observation'] and summary['scheduled']['valid_responses'] == 60
base, tree = best['candidate_commit'], best['candidate_tree']
assert base == 'dda361dcd45f2eee5cff5402a3d8b8a5421ddd33' and tree == 'ad41cd32f93433b1be065fc8d1969d8da78f2600'
assert git(SITE, 'rev-parse', 'HEAD') == base and git(SITE, 'rev-parse', 'HEAD^{tree}') == tree
assert not git(SITE, 'status', '--porcelain') and not git(PRODUCTION, 'status', '--porcelain')
assert git(PRODUCTION, 'rev-parse', 'HEAD') == summary['production_merge_commit'] == '119cd5561e1b26d125eff96ad6cf8cc779dbf17e'
assert git(PRODUCTION, 'rev-parse', 'HEAD^{tree}') == tree
assert ROOT.joinpath('r18-production-index.html').read_bytes() == SITE.joinpath('index.html').read_bytes()
write('candidate-pool-before.json', pool)

parent = INSTANCE / 'runs/round-10-shared-scholarly-entity'
parent_change = json.loads(parent.joinpath('change.json').read_text())
old_seed = parent_change['base_production_commit']
old_commit = parent_change['candidate_commit']
assert old_commit == '04e7ea4d0b1a6be0c65301c2a297e401294a0b78'
assert git(SITE, 'rev-parse', old_commit + '^{tree}') == parent_change['candidate_tree']
assert git(SITE, 'diff', '--name-only', old_seed, old_commit).splitlines() == FILES
pattern = r'<script type="application/ld\+json">.*?</script>'
old_schema = json.loads(parent.joinpath('schema-after.json').read_text())
operations, source_hashes = [], {}
for name in FILES:
    before_html = subprocess.check_output(['git','-C',str(SITE),'show',old_seed + ':' + name],text=True)
    after_html = subprocess.check_output(['git','-C',str(SITE),'show',old_commit + ':' + name],text=True)
    before = re.findall(pattern,before_html,re.S)
    after = re.findall(pattern,after_html,re.S)
    assert len(before) == len(after) == 1
    assert before_html.replace(before[0],after[0],1) == after_html, name
    assert re.findall(pattern,SITE.joinpath(name).read_text(),re.S) == before, name
    payload = json.loads(after[0].split('>',1)[1].rsplit('</script>',1)[0])
    assert payload == old_schema[name], name
    operations.append({'op':'replace_text','node':'meta:schema' if name == 'index.html' else 'file:' + name,
        'before':before[0],'after':after[0]})
    source_hashes[name] = {'r10_before_sha256':hashlib.sha256(before[0].encode()).hexdigest(),
        'r10_after_sha256':hashlib.sha256(after[0].encode()).hexdigest()}
original_home_op = json.loads(parent.joinpath('operations.json').read_text())['operations']
assert original_home_op == operations[:1], 'Reuse the corrected final R10 operation, not the initial attempt'
write('operations.json', {'operations':operations})
write('wrapper-operations.json', {'operations':operations[:1]})
write('manual-operations.json', {'reason':'Support HTML nodes are not mutable text-file nodes in the existing graph; apply these three exact replacements with apply_patch in the allocated worktree. No core change.', 'operations':operations[1:]})
ROOT.joinpath('parents').mkdir(exist_ok=True)
for name in ['operations.json','schema-before.json','schema-after.json','schema-contract.json']:
    shutil.copy2(parent / name, ROOT / 'parents' / ('r10-' + name))
shutil.copy2(previous / 'operations.json',ROOT / 'parents/r18-operations.json')
write('combination-source.json', {'parents':['r18','r10'], 'seed_commit':base,'seed_tree':tree,
    'r10_commit':old_commit,'r10_tree':parent_change['candidate_tree'],'r10_seed_commit':old_seed,
    'source':'Final measured R10 commit and schema-after.json, not operations-initial-attempt.json',
    'four_r10_files_reproduced_exactly_from_r9_with_schema_only':True,
    'r18_seed_schema_matches_r9_in_all_four_files':True,'schema_block_hashes':source_hashes,
    'parent_artifact_sha256':{p.name:digest(p) for p in sorted(ROOT.joinpath('parents').iterdir())},
    'applied_operations':4,'inherited_r18_routing_operations':9,
    'interpretation':'New unmeasured combination; R10 6/60 discard and R18 12/60 keep are historical observations, not additive effects or a lift prediction.'})
selected = {'id':SELECTED,'status':'selected_preparing','measured':False,'round':19,'change_id':CHANGE_ID,
    'parents':['r18','r10'],'retain_for_combinations':True,'files':FILES,'base_commit':base,
    'modules':['homepage-identity','method-reference','research-context','paper-authority','reference-pages'],
    'hypothesis':'Test the exact retained R10 shared ScholarlyArticle identity and page-specific WebPage metadata now that R18 exposes paper, method and context pages in actual source URLs.',
    'reason_selected':'R18 has five support-page URL cells across all three reference pages, including two fuzzy citations; cross-page machine-readable identity is a coherent retained candidate to retest, not a proven source of lift.',
    'scope':'Four exact archived JSON-LD block replacements only; every non-JSON-LD byte, visible fact and alphaXiv reading destination remains unchanged.',
    'module_dependencies':['One shared canonical #paper entity','One page-specific #webpage per document',
        'Each page mainEntity points to the same paper','R18 routing, R17 static method, R16 H2s and R9 evidence retained'],
    'interpretation':'R10 remains a measured discard; this R18/R10 combination receives its own future measurement. Do not add parent scores.'}
pool['proposals'].append(selected)
write('new-proposals.json',[selected])

ROOT.joinpath('control').mkdir(exist_ok=True)
for name in ['summary.json','search-matrix.csv','search-map.json']:
    shutil.copy2(live / name,ROOT / 'control' / name)
for name in ['outer_metric.py','queries.txt','search-map.json']:
    shutil.copy2(previous / name,ROOT / name)
shutil.copy2(live / 'collection-settings.json',ROOT / 'collection-settings.json')
assert digest(ROOT / 'queries.txt') == 'f2440c27b9fa7596e902b5bc30a30130e10789564a75f661338742d40876d8ce'
assert digest(ROOT / 'control/search-matrix.csv') == 'f4c13a905941353d775de225ba6b2e38b2525f1f9116fee2bdaafb85a250a2a4'
registry = json.loads(previous.joinpath('outer-measurements.json').read_text())
matches = [r for r in registry['measurements'] if r['deployed_tree'] == tree]
assert len(matches) == 1 and matches[0]['label'] == 'r18-immediate-live'
control_record = copy.deepcopy(matches[0])
control_record.update({'label':'r18-best-reused-control','source_label':'r18-immediate-live',
    'matrix':'control/search-matrix.csv','measured_at':summary['measured_at'],
    'verification':'Preserved exact R18 tree and its complete 12/60 observation; historical control, not new R19 searches'})
write('outer-measurements.json',{'measurements':[control_record]})
write('production-context.json',{'production_commit':summary['production_merge_commit'],'production_tree':tree,
    'selection_seed_round':18,'selection_seed_commit':base,'selection_seed_tree':tree,
    'production_observation':summary['scheduled'],'best_observed_before':best,
    'production_unchanged':True,'requires_separate_publication_approval':True})
policy = copy.deepcopy(pool['policy'])
policy.update({'baseline':'Best complete R18: 12/60, primary 20.0, secondary composite 35.19444; historical control, not fresh/simultaneous. Keep requires strictly more than 12/60 with all 60 valid.',
    'current_production':'R18 unchanged, 12/60, keep; all user-requested alphaXiv routes retained',
    'deployment':'Separate explicit R19 approval required; verify exact candidate tree and all four changed served HTML resources before and after the real 60 requests',
    'history':'All nineteen R0–R18 observations, twelve old proposals and best_observed R18 unchanged; the new R18/R10 combination is unmeasured. Never add parent scores.'})
write('outer-only-policy.json',policy)
engine_files = {'gpt-web':'gpt-web-answers.jsonl','codex-search':'codex-answers-complete.jsonl',
    'tavily-search':'tavily-answers.jsonl','exa-search':'exa-answers.jsonl'}
ROOT.joinpath('r18-evidence').mkdir(exist_ok=True)
for name in ['summary.json',*engine_files.values()]:
    shutil.copy2(live / name,ROOT / 'r18-evidence' / name)
queries = ROOT.joinpath('queries.txt').read_text().splitlines()
answers = {e:{r['query']:r for r in map(json.loads,ROOT.joinpath('r18-evidence',name).read_text().splitlines())} for e,name in engine_files.items()}
assert all(len(rows) == 15 and set(rows) == set(queries) and all(r['status'] == 'ok' for r in rows.values()) for rows in answers.values())
write('r18-search-evidence.json',{'tool':'Saved actual R18 four-engine answers; not new R19 searches',
    'result_scope':'Displayed source URLs only, not traffic, top-ten ranks or a prediction of combination lift',
    'observations':[{'query_id':f'Q{i:02d}','result_urls':list(dict.fromkeys(u.rstrip('.,;:!?*_') for e in engine_files for u in URL_RE.findall(answers[e][q]['text']))),
        'raw_file':'r18-evidence/gpt-web-answers.jsonl','raw_files':{e:'r18-evidence/' + name for e,name in engine_files.items()}} for i,q in enumerate(queries,1)]})
support = [r for r in json.loads(live.joinpath('explicit-project-urls.json').read_text()) if any(re.search(r'/(method|paper|research-context)\.html',u) for u in r['urls'])]
assert len(support) == summary['explicit_support_page_url_cells'] == 5
write('observed-entry-surfaces.json',{'source_round':18,'cells':support,'inference_limit':'Actual source visibility motivates a test; does not establish the proposed metadata change will improve retrieval or citations.'})
actions = {'homepage-identity':'Replay final R10 homepage JSON-LD; preserve every visible identity/heading and R18 alphaXiv anchor',
    'method-reference':'Replay page-specific WebPage and shared paper entity; method text and static R17 reference remain',
    'research-context':'Replay metadata only on the observed fuzzy-query entry page; no new topic or text',
    'paper-authority':'Replay shared scholarly identity with existing authors/year/identifier; citation meta/PDF/BibTeX stay unchanged',
    'machine-readable-summary':'Keep llms.txt and alphaXiv Paper entry unchanged',
    'repository-authority':'Keep README and alphaXiv Paper entry unchanged; no external repository changes',
    'crawler-routing':'Keep robots/sitemap; do not infer indexing from served bytes or graph reach',
    'presentation':'Keep all body HTML, scripts, styles, navigation and layout byte-unchanged',
    'reference-pages':'Align shared identity across the three actual R18 source pages; original R8 footer routes retained',
    'external-paper-entry':'Keep outbound alphaXiv routing; external backlink state unknown, no author-owned edit'}
assert set(actions) == {m['id'] for m in pool['modules']}
write('module-review.json',{'basis':'Complete R18 observation, all retained candidates and final R10 archive; no new R19 probes',
    'latest_observation':{'round':18,'project_citations':12,'explicit_project_url_cells':11,'explicit_support_page_url_cells':5,
        'fuzzy_citations':2,'broad_citations':1,'decision':'keep'},
    'reviews':[{'module':k,'action':v} for k,v in actions.items()],
    'alternatives_retained':[{'id':p['id'],'status':p['status'],'measured':p.get('measured',False),
        'action':'Retain unchanged; exact R10 schema alone is replayed in a separately identified combination' if p['id']=='shared-scholarly-entity' else 'Retain unchanged; do not silently merge another bundle'} for p in pool['proposals'] if p['id'] != SELECTED],
    'limitations':'R10 was 6/60 against historical R9 8/60; no predicted interaction gain and no addition of parent scores.'})
config = json.loads(previous.joinpath('config.json').read_text())
config['interventions'][0] = {'id':CHANGE_ID,'candidate_id':CHANGE_ID,'nodes':['meta:schema'],
    'manual_files':FILES[1:],'graph_scope':'One supported homepage metadata operation and three explicitly validated apply_patch support-file operations; no graph/core expansion',
    'source_url':'https://eau-meta-agent.github.io/method.html','link_state':'present',
    'link_evidence_url':'https://eau-meta-agent.github.io/method.html', 'change_kind':'node',
    'local_state':'R18 actually returns method/context/paper URLs; each page currently declares a separate ScholarlyArticle without a common @id',
    'hypothesis':selected['hypothesis'],'candidate_arms':[{'id':p['id'],'status':p['status'],'hypothesis':p['hypothesis']} for p in pool['proposals']]}
config['interventions'][1]['hypothesis'] = 'External paper edits need separate author authority and are outside R19'
write('config.json',config)
write('change.json',{'round':19,'change_id':CHANGE_ID,'pool_candidate_id':SELECTED,'state':'preparing',
    'files':FILES,'graph_nodes':['meta:schema'],'manual_files':FILES[1:],
    'selection_seed_round':18,'selection_seed_commit':base,'selection_seed_tree':tree,
    'current_production_commit':summary['production_merge_commit'],'current_production_tree':tree,
    'parents':selected['parents'],'hypothesis':selected['hypothesis'],'selection':policy,
    'knowledge_map_sha256':digest(INSTANCE / 'map.json'),
    'technical_references':['https://schema.org/mainEntity','https://schema.org/mainEntityOfPage','https://www.w3.org/TR/json-ld11/#node-identifiers'],
    'unchanged_vs_seed':['Every non-JSON-LD byte','all visible text and factual claims','all R18 alphaXiv anchors/config/README/llms entries',
        'all non-JSON-LD metadata and canonical URLs','PDF/citation fields/BibTeX','R17 static method/R16 H2s/R9 data',
        'scripts/styles/assets/crawler files','map/queries/judge/normalizer/engine settings'],
    'deployment_plan':'Require separate R19 approval, recheck then-current main for teammate changes, verify exact full tree plus all four changed served resources before and after collection.'})
cli('scan','--no-interactive',name='wrapper-scan.txt')
cli('configure','--part','index.html','--metric','live_project_citation_rate','--metric-goal','maximize',
    '--metric-command',f'python3 {ROOT / "outer_metric.py"}','--mode','sequential','--rounds','1',
    '--metric-timeout','120','--no-interactive',name='wrapper-configure.txt')
run = json.loads(cli('run','--part','index.html','--no-interactive','--json',name='wrapper-run.json'))
pool.update({'current_round':19,'selected_candidate_id':SELECTED,'policy':policy,'updated_at':dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')})
assert pool['best_observed'] == best and digest(pool_path) == old_hash
write('candidate-pool-selected.json',pool)
pool_path.write_text(json.dumps(pool,ensure_ascii=False,indent=2) + '\n')
print(json.dumps({'run':run,'selected':SELECTED,'parents':selected['parents'],'seed_round':18,
    'old_proposals_preserved':12,'history_count':19,'schema_operations':4,'inner_score':'not computed'},indent=2))
