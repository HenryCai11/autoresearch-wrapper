"""Require the exact R19 tree, four served resources, and bounded request times."""
import datetime as dt
from common import *

assert os.environ.get('SLURM_JOB_ID')
LIVE = ROOT / 'r19-live'
change = json.loads(ROOT.joinpath('change.json').read_text())
commit, tree = git(PRODUCTION, 'rev-parse', 'HEAD'), git(PRODUCTION, 'rev-parse', 'HEAD^{tree}')
assert commit == 'ab6847afc14de3a9067361b071605de711c96337'
assert tree == change['candidate_tree'] == '12b28c84303366ae8e4117709ec0166c1919ae9a'
assert not git(PRODUCTION, 'status', '--porcelain')
resources = {}
for name in FILES:
    before = LIVE.joinpath('served-before', name).read_bytes()
    after = LIVE.joinpath('served-after', name).read_bytes()
    assert before == after == PRODUCTION.joinpath(name).read_bytes()
    assert before == Path(change['candidate']['worktree_path']).joinpath(name).read_bytes()
    resources[name] = digest(LIVE / 'served-before' / name)
queries = ROOT.joinpath('queries.txt').read_text().splitlines()

def moment(value):
    return dt.datetime.fromisoformat(value.strip().replace('Z', '+00:00'))

before_text = LIVE.joinpath('verified-before.txt').read_text().strip()
after_text = LIVE.joinpath('verified-after.txt').read_text().strip()
before_time, after_time = moment(before_text), moment(after_text)
assert before_time < after_time
starts, ends = [], []
for group, expected in [(1, 8), (2, 7)]:
    group_dir = LIVE / f'codex-group-{group}'
    rows = [json.loads(line) for line in group_dir.joinpath('answers.jsonl').read_text().splitlines()]
    assert len(rows) == expected and all(row['status'] == 'ok' and row['text'].strip() for row in rows)
    start = moment(group_dir.joinpath('started-at.txt').read_text())
    end = moment(group_dir.joinpath('completed-at.txt').read_text())
    assert before_time <= start <= end <= after_time
    starts.append(start)
    ends.append(end)
gpt = [json.loads(line) for line in LIVE.joinpath('gpt-web-answers.jsonl').read_text().splitlines()]
assert len(gpt) == 15 and {r['query'] for r in gpt} == set(queries)
for row in gpt:
    assert row['status'] == 'ok' and row['text'].strip()
    start, end = moment(row['started_at']), moment(row['measured_at'])
    assert before_time <= start <= end <= after_time
    starts.append(start)
    ends.append(end)
events = [json.loads(line) for line in LIVE.joinpath('network-events.jsonl').read_text().splitlines()]
assert len(events) == 30 and {(r['query'], r['provider']) for r in events} == {(q, p) for q in queries for p in ['tavily', 'exa']}
for row in events:
    assert row['http'] == '200' and row['exit_code'] == 0
    start, end = moment(row['started_at']), moment(row['ended_at'])
    assert before_time <= start <= end <= after_time
    starts.append(start)
    ends.append(end)
for name in ['tavily-answers.jsonl', 'exa-answers.jsonl']:
    rows = [json.loads(line) for line in LIVE.joinpath(name).read_text().splitlines()]
    assert len(rows) == 15 and {r['query'] for r in rows} == set(queries)
    assert all(r['status'] == 'ok' and r['text'].strip() for r in rows)
for phase in ['before', 'after']:
    assert LIVE.joinpath(f'origin-main-{phase}.txt').read_text().split()[0] == commit
record = {'source_branch': 'codex/geo-live-round-19-deploy', 'candidate_branch': 'codex/geo-live-round-19',
    'candidate_commit': change['candidate_commit'], 'deploy_commit': '82150175332c44981e5ba25ae8afba35d826a57c',
    'production_merge_commit': commit, 'production_tree': tree, 'production_url': 'https://eau-meta-agent.github.io/',
    'resource_sha256': resources, 'served_version_verified_at': before_text, 'served_version_reverified_at': after_text,
    'collection_timing_verified': True, 'first_request_at': min(starts).isoformat(),
    'last_completed_request_at': max(ends).isoformat(),
    'timing_evidence': 'GPT/API per-request timestamps and both Codex group start/completion markers are within served checks; all 60 valid before record creation.',
    'verification': 'All four changed resources byte-match the exact candidate and merged production tree before collection and after all requests finish.',
    'authorization': 'User explicitly requested publishing and testing the prepared R19 candidate.',
    'selection_seed': 'R18 best complete observation, 12/60; preserved historical control, not fresh or simultaneous',
    'deployment_method': 'Isolated branch on then-current R18 main; replay the exact retained final R10 JSON-LD blocks, full tree match before merge. Four schema-only replacements; every body/non-JSON-LD byte and all R18 alphaXiv routes retained. R10 and R18 old results are not added to predict this combination.',
    'traffic_status': 'No alphaXiv click or visit measurement; changing outbound destinations does not prove traffic uplift.'}
for branch_key, commit_key in [('source_branch', 'deploy_commit'), ('candidate_branch', 'candidate_commit')]:
    assert git(PRODUCTION, 'rev-parse', 'origin/' + record[branch_key]) == record[commit_key]
LIVE.joinpath('deployment.json').write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(record, indent=2))
