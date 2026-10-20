"""Verify complete R21 evidence, exact retained insertion and immutable history."""
import csv
import shutil
import sys
from common import *

assert os.environ.get('SLURM_JOB_ID')
ROUND,LIVE = DEST,DEST / 'r21-live'
summary = json.loads(LIVE.joinpath('summary.json').read_text())
pool = json.loads(INSTANCE.joinpath('candidate-pool.json').read_text())
original = json.loads(ROUND.joinpath('candidate-pool-before.json').read_text())
before_record = json.loads(LIVE.joinpath('candidate-pool-before-record.json').read_text())
assert {h['id'] for h in pool['history']} == {f'r{i}' for i in range(22)}
assert pool['history'][:-1] == before_record['history'] == original['history']
assert all(h['retain_for_combinations'] for h in pool['history'])
assert len(pool['proposals']) == 15 and len(original['proposals']) == 14 and all(p in pool['proposals'] for p in original['proposals'])
chosen = next(p for p in pool['proposals'] if p['id'] == SELECTED)
assert chosen['measured'] is True and chosen['status'] == summary['decision'] and chosen['parents'] == ['r18','r14']
assert next(p for p in pool['proposals'] if p['id'] == 'static-second-backbone-evidence')['status'] == 'discard'
assert {p['id'] for p in pool['proposals'] if not p.get('measured',False)} == {'external-paper-link-audit'}
queries = ROUND.joinpath('queries.txt').read_text().splitlines()
rows = list(csv.DictReader(LIVE.joinpath('search-matrix.csv').open(newline='')))
expected = {(q,e) for q in queries for e in ['gpt-web','codex-search','tavily-search','exa-search']}
assert len(rows) == 60 and {(r['query'],r['engine']) for r in rows} == expected
assert all(r['answer_empty'] == 'False' for r in rows)
citations = sum(r['site_cited'] == 'True' for r in rows)
assert citations == summary['scheduled']['project_citations']
assert summary['decision'] == ('keep' if citations > 12 else 'discard')
integrity = json.loads(LIVE.joinpath('integrity.json').read_text())
for name,sha in integrity['sha256'].items():
    assert digest(LIVE / name) == sha,name
assert digest(ROUND.parent / 'round-18-alphaxiv-paper-routing/r18-live/search-matrix.csv') == integrity['baseline_matrix_sha256'] == 'f4c13a905941353d775de225ba6b2e38b2525f1f9116fee2bdaafb85a250a2a4'
assert set(integrity['served_resources_sha256']) == set(DEPLOY_FILES)
for name,sha in integrity['served_resources_sha256'].items():
    for phase in ['before','after']:
        assert digest(LIVE / f'served-{phase}' / name) == sha
for name in ['gpt-web-answers.jsonl','codex-answers-complete.jsonl','tavily-answers.jsonl','exa-answers.jsonl']:
    answers = [json.loads(line) for line in LIVE.joinpath(name).read_text().splitlines()]
    assert len(answers) == 15 and {r['query'] for r in answers} == set(queries)
    assert all(r['status'] == 'ok' and r['text'].strip() for r in answers)
gpt_raw = [json.loads(line) for line in LIVE.joinpath('gpt-web-raw-responses.jsonl').read_text().splitlines()]
gpt = [json.loads(line) for line in LIVE.joinpath('gpt-web-answers.jsonl').read_text().splitlines()]
assert len(gpt_raw) == 15 and all(r['raw'] == a['text'] and r['query'] == a['query'] for r,a in zip(gpt_raw,gpt))
events = [json.loads(line) for line in LIVE.joinpath('network-events.jsonl').read_text().splitlines()]
assert len(events) == 30 and all(e['http'] == '200' and e['exit_code'] == 0 for e in events)
change = json.loads(ROUND.joinpath('change.json').read_text())
worktree = Path(change['candidate']['worktree_path'])
replays = {}
for name,count in [('seed',12),('candidate-001',citations)]:
    result = subprocess.run([sys.executable,str(ROUND / 'outer_metric.py')],cwd=worktree.parent / name,check=True,capture_output=True,text=True)
    value = float(next(line.split('=',1)[1] for line in result.stdout.splitlines() if line.startswith('METRIC=')))
    assert abs(value - 100*count/60) < 1e-9
    replays[name] = result.stdout.strip()
prep = json.loads(ROUND.joinpath('audit.json').read_text())
for name,sha in prep['sha256'].items():
    path = LIVE / 'pre-live-README.md' if name == 'README.md' else LIVE / 'pre-live-outer-measurements.json' if name == 'outer-measurements.json' else ROUND / name
    assert digest(path) == sha,'Preparation changed: ' + name
assert ROUND.joinpath('operations.json').read_bytes() == ROUND.joinpath('parents/r14-operations.json').read_bytes()
operations = json.loads(ROUND.joinpath('operations.json').read_text())['operations']
assert len(operations) == 1
op = operations[0]
seed_html = worktree.parent.joinpath('seed/index.html').read_text()
assert seed_html.count(op['before']) == 1
assert seed_html.replace(op['before'],op['after'],1) == worktree.joinpath('index.html').read_text() == ROUND.joinpath('site/index.html').read_text()
assert all(worktree.joinpath(n).read_bytes() == worktree.parent.joinpath('seed',n).read_bytes() for n in HTML if n != 'index.html')
source = json.loads(ROUND.joinpath('source-verification.json').read_text())
assert source['row_count'] == 9 and source['numeric_value_count'] == 36 and digest(worktree / 'script.js') == source['script_sha256']
assert all(json.loads(ROUND.joinpath('validation.json').read_text())['checks'].values())
selection = json.loads(LIVE.joinpath('best-observed-selection.json').read_text())
assert selection['previous_best'] == before_record['best_observed'] == original['best_observed']
assert selection['selected_best'] == pool['best_observed'] and selection['promoted'] is (summary['decision'] == 'keep')
if selection['promoted']:
    assert pool['best_observed']['round'] == 21 and pool['best_observed']['outer_observation'] == summary['scheduled']
else:
    assert pool['best_observed'] == before_record['best_observed']
assert chosen['measurement_artifact_dir'] == 'runs/round-21-descriptive-static-evidence-combination/r21-live'
deployment = json.loads(LIVE.joinpath('deployment.json').read_text())
assert deployment['production_tree'] == git(worktree,'rev-parse','HEAD^{tree}') == git(PRODUCTION,'rev-parse','HEAD^{tree}')
assert deployment['collection_timing_verified'] and deployment['changed_files_vs_live_r20'] == DEPLOY_FILES
assert not git(worktree,'status','--porcelain') and not git(PRODUCTION,'status','--porcelain')
routing = json.loads(ROUND.joinpath('parents/r18-operations.json').read_text())['operations']
assert len(routing) == 9 and all(worktree.joinpath(op['node'][5:]).read_text().count(op['after']) == 1 for op in routing)
scripts = ['prepare_publication.py','prepare_publication.sh','record_deployment.py','summarize_outer_live.py','finalize_r21_measurement.py',
    'archive_r21_live.py','audit_r21.py','verify_served.sh','collect_api.sh','normalize_api.py','normalize_api.sh',
    'collect_codex_network.sh','probe_codex_native.sh','finish_r21.sh']
script_hashes = {}
for name in scripts:
    target = LIVE / 'scripts' / name
    assert not target.exists()
    target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(ROOT / name,target)
    script_hashes[name] = digest(target)
shutil.copy2(ROOT / 'publication-intent.json',LIVE / 'publication-intent.json')
context = json.loads(LIVE.joinpath('execution-context.json').read_text())
accounting = subprocess.check_output(['sacct','--jobs',','.join(context['slurm_jobs']),'--noheader','--parsable2','--format=JobIDRaw,JobName,State,ExitCode'],text=True)
LIVE.joinpath('slurm-provenance.json').write_text(json.dumps({'preparation_and_normalization_jobs':context['slurm_jobs'],
    'scoring_archive_audit_job':os.environ['SLURM_JOB_ID'],'accounting_before_scoring_job_completion':accounting,
    'network_only_acquisition':'GPT web tool; curl/jq Tavily/Exa; existing native Codex CLI, same prompt/flags/90s/low/8+7 groups; no local inference',
    'slurm_only':'All Python, normalization, scoring, wrapper CLI and archival checks; 1 CPU, 1 GB per job'},indent=2) + '\n')
report = {'passed':True,'cells':60,'project_citations':citations,'history_count':len(pool['history']),'old_proposals_preserved':14,
    'proposal_count':len(pool['proposals']),'unmeasured_proposals':1,'served_changed_resources':3,'exact_r14_operations':1,
    'source_rows':9,'source_numeric_values':36,'frozen_queries_settings_judge':True,'alpha_routing_retained':True,
    'no_successful_answer_resampled':True,'archived_metric_replays':replays,'best_observed_round':pool['best_observed']['round'],'script_sha256':script_hashes,
    'sha256':{p.relative_to(LIVE).as_posix():digest(p) for p in sorted(LIVE.rglob('*')) if p.is_file()}}
LIVE.joinpath('audit.json').write_text(json.dumps(report,indent=2) + '\n')
print(json.dumps({k:v for k,v in report.items() if k != 'sha256'},indent=2))
