"""Record exact R17 deployment and require all collection to fall between served checks."""
import datetime as dt
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LIVE = ROOT / 'r17-live'
SITE = Path('/project/aip-xiye17/henrycai/eau-meta-agent.github.io')
commit = subprocess.check_output(['git', '-C', str(SITE), 'rev-parse', 'HEAD'], text=True).strip()
tree = subprocess.check_output(['git', '-C', str(SITE), 'rev-parse', 'HEAD^{tree}'], text=True).strip()
assert commit == '6eb91c2d44003afe248e5e2623a2a6a2f38f5675'
assert tree == 'acbe04ac17e69189e3eb630ed9c89e449b8faa44'
assert not subprocess.check_output(['git', '-C', str(SITE), 'status', '--porcelain'], text=True).strip()
before = LIVE.joinpath('served-before/index.html').read_bytes()
after = LIVE.joinpath('served-after/index.html').read_bytes()
assert before == after == SITE.joinpath('index.html').read_bytes()
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
    lines = [json.loads(line) for line in group_dir.joinpath('answers.jsonl').read_text().splitlines()]
    assert len(lines) == expected and all(row['status'] == 'ok' and row['text'].strip() for row in lines)
    start = moment(group_dir.joinpath('started-at.txt').read_text())
    end = moment(group_dir.joinpath('completed-at.txt').read_text())
    assert before_time <= start <= end <= after_time
    starts.append(start)
    ends.append(end)
gpt = [json.loads(line) for line in LIVE.joinpath('gpt-web-answers.jsonl').read_text().splitlines()]
assert len(gpt) == 15 and {row['query'] for row in gpt} == set(queries)
for row in gpt:
    assert row['status'] == 'ok' and row['text'].strip()
    start, end = moment(row['started_at']), moment(row['measured_at'])
    assert before_time <= start <= end <= after_time
    starts.append(start)
    ends.append(end)
events = [json.loads(line) for line in LIVE.joinpath('network-events.jsonl').read_text().splitlines()]
assert len(events) == 30 and {(row['query'], row['provider']) for row in events} == {(query, provider) for query in queries for provider in ['tavily', 'exa']}
for row in events:
    assert row['http'] == '200' and row['exit_code'] == 0
    start, end = moment(row['started_at']), moment(row['ended_at'])
    assert before_time <= start <= end <= after_time
    starts.append(start)
    ends.append(end)
for name in ['tavily-answers.jsonl', 'exa-answers.jsonl']:
    answers = [json.loads(line) for line in LIVE.joinpath(name).read_text().splitlines()]
    assert len(answers) == 15 and {r['query'] for r in answers} == set(queries)
    assert all(r['status'] == 'ok' and r['text'].strip() for r in answers)
for phase in ['before', 'after']:
    assert LIVE.joinpath(f'origin-main-{phase}.txt').read_text().split()[0] == commit
record = {
    'source_branch': 'codex/geo-live-round-17-deploy', 'candidate_branch': 'codex/geo-live-round-17',
    'candidate_commit': 'dcf0b80e0e0554746e94e3e47034d77174b35417',
    'deploy_commit': '20b5aaf7f2cc7d44ab4825a2599cc9cc1dcd61ba',
    'production_merge_commit': commit, 'production_tree': tree, 'production_url': 'https://eau-meta-agent.github.io/',
    'resource_sha256': {'index.html': hashlib.sha256(before).hexdigest()},
    'served_version_verified_at': before_text, 'served_version_reverified_at': after_text,
    'collection_timing_verified': True, 'first_request_at': min(starts).isoformat(),
    'last_completed_request_at': max(ends).isoformat(),
    'timing_evidence': 'GPT and API request timestamps plus both Codex group start/completion markers are all within the before/after served checks. All 60 responses are valid before record creation.',
    'verification': 'The only changed resource index.html byte-matches the exact candidate and production tree before collection and after every search request has completed.',
    'authorization': 'User explicitly requested publishing and testing the prepared R17 candidate.',
    'selection_seed': 'R16 preserved best, 9/60; exact current R16 production tree is the historical selection control',
    'deployment_method': 'An isolated deploy branch based on R16 was patched to the exact R16-based R17 candidate; full tree verified before merge. Only the exact retained R13 static environment/agent reference is inserted. Both R16 H2s, interactive explorer, result data, all other sections, pages, metadata, scripts and styles remain unchanged. Parent scores are not inferred or added.'
}
for branch_key, commit_key in [('source_branch', 'deploy_commit'), ('candidate_branch', 'candidate_commit')]:
    branch_commit = subprocess.check_output(['git', '-C', str(SITE), 'rev-parse', 'origin/' + record[branch_key]], text=True).strip()
    assert branch_commit == record[commit_key]
LIVE.joinpath('deployment.json').write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(record, indent=2))
