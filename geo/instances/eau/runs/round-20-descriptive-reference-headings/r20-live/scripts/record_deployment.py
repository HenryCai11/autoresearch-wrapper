"""Bind the real R20 collection to exact deployment and served-byte time bounds."""
import datetime as dt
from common import *

assert os.environ.get('SLURM_JOB_ID')
LIVE = ROOT / 'r20-live'
change = json.loads(ROOT.joinpath('change.json').read_text())
intent = json.loads(ROOT.joinpath('publication-intent.json').read_text())
published = json.loads(LIVE.joinpath('published.json').read_text())
commit,tree = git(PRODUCTION,'rev-parse','HEAD'),git(PRODUCTION,'rev-parse','HEAD^{tree}')
assert commit == published['production_merge_commit'] and tree == published['production_tree'] == change['candidate_tree']
assert not git(PRODUCTION,'status','--porcelain')
resources = {}
for name in HTML:
    before,after = LIVE.joinpath('served-before',name).read_bytes(),LIVE.joinpath('served-after',name).read_bytes()
    assert before == after == PRODUCTION.joinpath(name).read_bytes() == Path(change['candidate']['worktree_path']).joinpath(name).read_bytes()
    resources[name] = digest(LIVE / 'served-before' / name)
queries = ROOT.joinpath('queries.txt').read_text().splitlines()
moment = lambda text:dt.datetime.fromisoformat(text.strip().replace('Z','+00:00'))
before_text,after_text = [LIVE.joinpath('verified-' + phase + '.txt').read_text().strip() for phase in ['before','after']]
before_time,after_time = moment(before_text),moment(after_text)
assert before_time < after_time
starts,ends = [],[]
for group,count in [(1,8),(2,7)]:
    directory = LIVE / f'codex-group-{group}'
    rows = [json.loads(line) for line in directory.joinpath('answers.jsonl').read_text().splitlines()]
    assert len(rows) == count and all(r['status'] == 'ok' and r['text'].strip() for r in rows)
    start,end = moment(directory.joinpath('started-at.txt').read_text()),moment(directory.joinpath('completed-at.txt').read_text())
    assert before_time <= start <= end <= after_time
    starts.append(start)
    ends.append(end)
rows = [json.loads(line) for line in LIVE.joinpath('gpt-web-answers.jsonl').read_text().splitlines()]
assert len(rows) == 15 and {r['query'] for r in rows} == set(queries)
for row in rows:
    assert row['status'] == 'ok' and row['text'].strip()
    start,end = moment(row['started_at']),moment(row['measured_at'])
    assert before_time <= start <= end <= after_time
    starts.append(start)
    ends.append(end)
events = [json.loads(line) for line in LIVE.joinpath('network-events.jsonl').read_text().splitlines()]
assert len(events) == 30 and {(r['query'],r['provider']) for r in events} == {(q,p) for q in queries for p in ['tavily','exa']}
for row in events:
    assert row['http'] == '200' and row['exit_code'] == 0
    start,end = moment(row['started_at']),moment(row['ended_at'])
    assert before_time <= start <= end <= after_time
    starts.append(start)
    ends.append(end)
for name in ['tavily-answers.jsonl','exa-answers.jsonl']:
    rows = [json.loads(line) for line in LIVE.joinpath(name).read_text().splitlines()]
    assert len(rows) == 15 and {r['query'] for r in rows} == set(queries)
    assert all(r['status'] == 'ok' and r['text'].strip() for r in rows)
for phase in ['before','after']:
    assert LIVE.joinpath(f'origin-main-{phase}.txt').read_text().split()[0] == commit
for branch,key in [(intent['deploy_branch'],'deploy_commit'),(intent['candidate_branch'],'candidate_commit')]:
    assert git(PRODUCTION,'rev-parse','origin/' + branch) == intent[key]
record = {'source_branch':intent['deploy_branch'],'candidate_branch':intent['candidate_branch'],
    'candidate_commit':change['candidate_commit'],'deploy_commit':intent['deploy_commit'],
    'production_merge_commit':commit,'production_tree':tree,'production_url':'https://eau-meta-agent.github.io/',
    'resource_sha256':resources,'served_version_verified_at':before_text,'served_version_reverified_at':after_text,
    'collection_timing_verified':True,'first_request_at':min(starts).isoformat(),'last_completed_request_at':max(ends).isoformat(),
    'timing_evidence':'GPT/API per-request timestamps and both Codex group start/completion markers fall within successful four-page served checks.',
    'authorization':intent['authorization'],'selection_seed':'R18 original best complete 12/60 historical control, not tied R19 matrix or a fresh simultaneous control',
    'deployment_method':intent['deployment_method'],'changed_files_vs_live_r19':HTML,'changed_files_vs_r18':FILES,
    'verification':'Exact complete candidate/production tree plus all four changed served resources match before and after collection.',
    'traffic_status':'alphaXiv reading routes retained; no click or visit measurement or traffic-lift claim'}
LIVE.joinpath('deployment.json').write_text(json.dumps(record,ensure_ascii=False,indent=2) + '\n')
print(json.dumps(record,indent=2))
