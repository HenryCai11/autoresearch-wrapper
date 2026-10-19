"""Verify complete R19 collection, exact parent replay and unchanged prior history."""
import csv
import shutil
import sys
from common import *

assert os.environ.get('SLURM_JOB_ID')
ROUND = DEST
LIVE = ROUND / 'r19-live'
summary = json.loads(LIVE.joinpath('summary.json').read_text())
pool = json.loads(INSTANCE.joinpath('candidate-pool.json').read_text())
original = json.loads(ROUND.joinpath('candidate-pool-before.json').read_text())
before_record = json.loads(LIVE.joinpath('candidate-pool-before-record.json').read_text())
assert {h['id'] for h in pool['history']} == {f'r{i}' for i in range(20)}
assert pool['history'][:-1] == before_record['history'] == original['history']
assert all(h['retain_for_combinations'] for h in pool['history'])
assert len(pool['proposals']) == 13 and len(original['proposals']) == 12
assert all(p in pool['proposals'] for p in original['proposals'])
chosen = next(p for p in pool['proposals'] if p['id'] == SELECTED)
assert chosen['measured'] is True and chosen['status'] == summary['decision'] and chosen['parents'] == ['r18','r10']
assert next(p for p in pool['proposals'] if p['id'] == 'shared-scholarly-entity')['status'] == 'discard'
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
for name,value in integrity['sha256'].items():
    assert digest(LIVE / name) == value,name
assert digest(ROUND.parent / 'round-18-alphaxiv-paper-routing/r18-live/search-matrix.csv') == integrity['baseline_matrix_sha256']
assert set(integrity['served_resources_sha256']) == set(FILES) and len(FILES) == 4
for name,value in integrity['served_resources_sha256'].items():
    for phase in ['before','after']:
        assert digest(LIVE / f'served-{phase}' / name) == value
for name in ['gpt-web-answers.jsonl','codex-answers-complete.jsonl','tavily-answers.jsonl','exa-answers.jsonl']:
    answers = [json.loads(line) for line in LIVE.joinpath(name).read_text().splitlines()]
    assert len(answers) == 15 and {r['query'] for r in answers} == set(queries)
    assert all(r['status'] == 'ok' and r['text'].strip() for r in answers)
change = json.loads(ROUND.joinpath('change.json').read_text())
worktree = Path(change['candidate']['worktree_path'])
replays = {}
for name,count in [('seed',12),('candidate-001',citations)]:
    result = subprocess.run([sys.executable,str(ROUND / 'outer_metric.py')],cwd=worktree.parent / name,
        check=True,capture_output=True,text=True)
    value = float(next(line.split('=',1)[1] for line in result.stdout.splitlines() if line.startswith('METRIC=')))
    assert abs(value - 100*count/60) < 1e-9
    replays[name] = result.stdout.strip()
prep = json.loads(ROUND.joinpath('audit.json').read_text())
for name,value in prep['sha256'].items():
    path = LIVE / 'pre-live-README.md' if name == 'README.md' else LIVE / 'pre-live-outer-measurements.json' if name == 'outer-measurements.json' else ROUND / name
    assert digest(path) == value,'Preparation changed: ' + name
operations = json.loads(ROUND.joinpath('operations.json').read_text())['operations']
assert len(operations) == 4
assert len(json.loads(ROUND.joinpath('wrapper-operations.json').read_text())['operations']) == 1
assert len(json.loads(ROUND.joinpath('manual-operations.json').read_text())['operations']) == 3
for name,op in zip(FILES,operations):
    seed_html = worktree.parent.joinpath('seed',name).read_text()
    assert seed_html.count(op['before']) == 1
    expected_html = seed_html.replace(op['before'],op['after'],1)
    assert worktree.joinpath(name).read_text() == expected_html == ROUND.joinpath('site',name).read_text()
manifest = json.loads(ROUND.joinpath('combination-source.json').read_text())
for name,value in manifest['parent_artifact_sha256'].items():
    assert digest(ROUND / 'parents' / name) == value
assert json.loads(ROUND.joinpath('schema-after.json').read_text()) == json.loads(ROUND.joinpath('parents/r10-schema-after.json').read_text())
assert all(json.loads(ROUND.joinpath('validation.json').read_text())['checks'].values())
selection = json.loads(LIVE.joinpath('best-observed-selection.json').read_text())
assert selection['previous_best'] == before_record['best_observed'] == original['best_observed']
assert selection['selected_best'] == pool['best_observed']
assert selection['promoted'] is (summary['decision'] == 'keep')
if selection['promoted']:
    assert pool['best_observed']['round'] == 19 and pool['best_observed']['outer_observation'] == summary['scheduled']
else:
    assert pool['best_observed'] == before_record['best_observed']
assert chosen['measurement_artifact_dir'] == 'runs/round-19-shared-entity-combination/r19-live'
assert 'alphaxiv.org/abs/2610.16523' in pool['policy']['user_routing_constraint']
deployment = json.loads(LIVE.joinpath('deployment.json').read_text())
assert deployment['production_tree'] == git(worktree,'rev-parse','HEAD^{tree}') == git(PRODUCTION,'rev-parse','HEAD^{tree}')
assert deployment['collection_timing_verified'] is True
assert not git(worktree,'status','--porcelain') and not git(PRODUCTION,'status','--porcelain')
scripts = ['record_deployment.py','summarize_outer_live.py','finalize_r19_measurement.py',
    'archive_r19_live.py','audit_r19.py','verify_served.sh','collect_api.sh','normalize_api.py','normalize_api.sh','finish_r19.sh']
script_hashes = {}
for name in scripts:
    target = LIVE / 'scripts' / name
    assert not target.exists()
    target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(ROOT / name,target)
    script_hashes[name] = digest(target)
report = {'passed':True,'cells':60,'project_citations':citations,'history_count':len(pool['history']),
    'old_proposals_preserved':12,'proposal_count':len(pool['proposals']),'unmeasured_proposals':1,
    'served_changed_resources':4,'exact_r10_schema_replay':True,'archived_metric_replays':replays,'script_sha256':script_hashes}
LIVE.joinpath('audit.json').write_text(json.dumps(report,indent=2) + '\n')
print(json.dumps(report,indent=2))
