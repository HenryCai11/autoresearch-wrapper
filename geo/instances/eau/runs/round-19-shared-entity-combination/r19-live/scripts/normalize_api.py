"""Normalize captured API replies offline with the frozen geo_eval formatter."""
import json
import os
from pathlib import Path
from geo_eval.search_api import format_ranked_results

assert os.environ.get('SLURM_JOB_ID')
ROOT = Path(__file__).resolve().parent
LIVE = ROOT / 'r19-live'
queries = ROOT.joinpath('queries.txt').read_text().splitlines()
events = [json.loads(line) for line in LIVE.joinpath('network-events.jsonl').read_text().splitlines()]
assert len(events) == 30
for provider,fields in [('tavily', ('content',)), ('exa', ('highlights', 'text', 'summary'))]:
    rows = []
    for i,query in enumerate(queries, 1):
        event = next(e for e in events if e['provider'] == provider and e['query'] == query)
        payload = json.loads(LIVE.joinpath(f'{provider}-raw/{i:02d}.json').read_text())
        text = format_ranked_results(payload, content_fields=fields) if event['http'] == '200' else ''
        status = 'ok' if event['http'] == '200' and event['exit_code'] == 0 and text.strip() else 'error'
        rows.append({'query': query, 'status': status, 'text': text, 'started_at': event['started_at'], 'measured_at': event['ended_at']})
    LIVE.joinpath(f'{provider}-answers.jsonl').write_text(''.join(json.dumps(row, ensure_ascii=False) + '\n' for row in rows))
    print(json.dumps({'provider': provider, 'responses': len(rows), 'valid': sum(row['status'] == 'ok' for row in rows)}))
