"""Preserve old candidates, append three hypotheses, and audit the unmeasured run."""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
INSTANCE = Path('/project/aip-xiye17/henrycai/autoresearch-wrapper/geo/instances/eau')
SITE = Path('/scratch/henrycai/eau-r12-20261016')
DEST = INSTANCE / 'runs/round-12-homepage-descriptive-h1'
change = json.loads(ROOT.joinpath('change.json').read_text())
validation = json.loads(ROOT.joinpath('validation.json').read_text())
run = json.loads(ROOT.joinpath('wrapper-run.json').read_text())
assert change['state'] == 'validated_awaiting_deployment_approval' and all(validation['checks'].values())
assert not DEST.exists()
pool = json.loads(INSTANCE.joinpath('candidate-pool.json').read_text())
old = json.loads(ROOT.joinpath('candidate-pool-before.json').read_text())
assert pool['history'] == old['history'] and len(pool['history']) == 12
assert all(proposal in pool['proposals'] for proposal in old['proposals'])
old_ids = {p['id'] for p in old['proposals']}
new_ids = {p['id'] for p in pool['proposals']} - old_ids
assert len(old_ids) == 5 and len(pool['proposals']) == 8
assert new_ids == {'homepage-descriptive-h1', 'static-second-backbone-evidence', 'static-component-reference'}
assert all(not p['measured'] and 'outer_observation' not in p for p in pool['proposals'] if p['id'] in new_ids)
registry = json.loads(ROOT.joinpath('outer-measurements.json').read_text())
assert len(registry['measurements']) == 1 and registry['measurements'][0]['deployed_tree'] == change['selection_seed_tree']
registry['measurements'][0]['matrix'] = '../round-9-static-benchmark-evidence/r9-live/search-matrix.csv'
ROOT.joinpath('portable-outer-measurements.json').write_text(json.dumps(registry, indent=2) + '\n')
evidence = json.loads(ROOT.joinpath('r11-search-evidence.json').read_text())
for item in evidence['observations']:
    item['raw_file'] = '../round-11-reference-cluster-without-r7/r11-live/gpt-web-answers.jsonl'
    item['raw_files'] = {engine: '../round-11-reference-cluster-without-r7/r11-live/' + Path(name).name for engine, name in item['raw_files'].items()}
ROOT.joinpath('portable-search-evidence.json').write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + '\n')
ROOT.joinpath('README.md').write_text(f'''# EAU R12 — descriptive homepage H1

Status: **validated local candidate; not published or measured**.

- Run: `{run['run_id']}`; sequential, one candidate, explicit index.html target.
- Selected pool proposal: `homepage-descriptive-h1`.
- Candidate: `{change['candidate_commit']}`; tree `{change['candidate_tree']}`.
- Selection seed: R9 `{change['selection_seed_commit']}`, recorded 8/60 citations
  and composite 30.25, all 60 valid; a reused historical control, not new searches.
- Current production: R11 `{change['current_production_commit']}`, recorded 7/60
  and composite 28.97; unchanged, and not the selection threshold.

## Intervention and dependency review

Only one line differs from R9: the visible primary heading changes from
“Learning to / evolve, together.” to “EAU: / Co-evolution.” The existing full
research title remains in the adjacent hero subtitle and document metadata.
The h1 id, single line break and emphasis markup remain. No new facts, results,
styles, scripts, links or metadata are introduced. All other R9 bytes remain,
including its R7 overview, R8 reference routes and R9 static benchmark data.
R10 and R11's unkept deltas and observations are retained in history, not silently
carried forward onto the best recorded seed.

R11 returned four explicit homepage URL cells and no support-page URLs. That
locates an observed entry page; it does not predict an H1 ranking benefit. The
existing h1 is a slogan without EAU, although the subtitle already names the
work. This candidate tests whether changing that one visible identity surface
affects the unchanged outer protocol. No lift is assumed.

The nine-module review is preserved in `module-review.json`. The five existing
proposals and R0–R11 history are unchanged. Three new hypotheses are appended:

| Proposal | State | Scope |
| --- | --- | --- |
| `homepage-descriptive-h1` | selected, unmeasured | Visible homepage identity |
| `static-second-backbone-evidence` | queued, unmeasured | Separately labelled existing Qwen2.5-7B-Instruct rows |
| `static-component-reference` | queued, unmeasured | Existing non-default explorer descriptions |

The external paper backlink proposal remains unknown and requires separate
author authority for an edit. None of the new hypotheses receives an inferred
score. Parent scores are not summed and discarded candidates are not deleted.

All {len(validation['checks'])} local checks passed. Visible homepage text:
{validation['visible_home_chars_before']} → {validation['visible_home_chars_after']}
characters, below the unchanged {validation['limit']} limit. No inner score was
computed. Checks cover exact scope, heading structure, IDs/links, unchanged
schema/static results and source hashes. They are not a browser or visual test;
actual rendered layout fit has not been verified.

## Publication and measurement gate

R12 has no registered live observation; its exact-tree metric guard refuses to
score it. A keep requires strictly more than R9's 8/60 citation cells with all
60 responses valid, using the same 15 queries and GPT web / Codex / Tavily / Exa
settings. The frozen judge counts bare project-domain mentions as citations;
explicit source URLs must be reported separately. A historical control and one
immediate sample cannot establish causality or exclude indexing delay.

After explicit publication approval, prepare an isolated deploy branch based on
current main and apply the exact candidate index.html. Do not blindly merge this
R9-based feature branch into R11, because that would retain the unkept R11
overview. Relative to R11, index.html differs in both the h1 and the restoration
of R9's overview; `production-to-candidate.patch` records the full change.
Verify the complete tree equals `{change['candidate_tree']}` before publishing,
then verify served homepage bytes before and after collection. Reconcile any
concurrent teammate edits before proceeding. Only real, complete observations
for that exact tree may be evaluated and recorded through the CLI.

Preparation, local checks and metric replay run through Slurm with one CPU and
1 GB memory. No publication, push, rollback, branch pruning, candidate deletion,
paid search collection or future follow-up was performed by this preparation.
''')
names = ['README.md', 'change.json', 'production-context.json', 'validation.json', 'operations.json',
    'heading-change.json', 'candidate.patch', 'production-to-candidate.patch', 'module-review.json', 'new-proposals.json',
    'config.json', 'graph-before.json', 'graph-after.json', 'priorities.json', 'decision.json', 'exploration.json',
    'preview.json', 'applied.json', 'candidate-pool-before.json', 'candidate-pool-selected.json', 'candidate-pool-after.json',
    'outer-only-policy.json', 'outer_metric.py', 'queries.txt', 'search-map.json', 'wrapper-run.json',
    'wrapper-candidate.json', 'seed-evaluation.json', 'seed-record.json', 'unpublished-metric-guard.txt',
    'prepare_r12.py', 'candidate_r12.py', 'archive_prepared_r12.py', 'prepare.sh']
paths = [(ROOT / name, DEST / name) for name in names]
paths += [(ROOT / 'portable-outer-measurements.json', DEST / 'outer-measurements.json'),
    (ROOT / 'portable-search-evidence.json', DEST / 'r11-search-evidence.json')]
run_dir = SITE / '.autoresearch-wrapper/runs' / run['run_id']
paths += [(run_dir / name, DEST / name) for name in ['program.md', 'results.tsv']]
for source, target in paths:
    assert source.is_file() and not target.exists(), source
    assert not re.search(r'(?i)tvly-[a-z0-9_-]{16,}|authorization:\s*bearer\s+[a-z0-9_-]{16,}|x-api-key\s*:\s*[a-z0-9_-]{16,}', source.read_text()), source.name
for source, target in paths:
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
worktree = Path(change['candidate']['worktree_path'])
assert not subprocess.check_output(['git', '-C', str(worktree), 'status', '--porcelain'], text=True).strip()
replay = subprocess.run([sys.executable, str(DEST / 'outer_metric.py')], cwd=worktree.parent / 'seed', capture_output=True, text=True, check=True)
assert 'LIVE_PROJECT_CITATIONS=8/60' in replay.stdout
guard = subprocess.run([sys.executable, str(DEST / 'outer_metric.py')], cwd=worktree, capture_output=True, text=True)
assert guard.returncode == 2 and 'No live measurement' in guard.stderr
environment = os.environ.copy()
environment.pop('PYTHONPATH', None)
status = subprocess.run(['bash', '/project/aip-xiye17/henrycai/autoresearch-wrapper/skills/autoresearch-wrapper-run/run.sh',
    'status', '--repo', str(SITE), '--json'], env=environment, capture_output=True, text=True, check=True)
DEST.joinpath('wrapper-status.json').write_text(status.stdout)
hashes = {path.relative_to(DEST).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(DEST.rglob('*')) if path.is_file()}
report = {'passed': True, 'local_checks': len(validation['checks']), 'history_count': 12,
    'existing_proposals_preserved': 5, 'new_proposals': sorted(new_ids), 'proposal_count': 8,
    'candidate_commit': change['candidate_commit'], 'candidate_tree': change['candidate_tree'],
    'seed_metric_replay': replay.stdout.strip(), 'candidate_guard_exit': guard.returncode,
    'outer_status': 'unmeasured; explicit approval and exact-tree deployment plus real 60-cell collection required', 'sha256': hashes}
DEST.joinpath('audit.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({key: value for key, value in report.items() if key != 'sha256'}, indent=2))
