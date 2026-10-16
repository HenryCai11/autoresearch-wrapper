"""Archive and audit an unmeasured R11 without mutating production or history."""
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
SITE = Path('/scratch/henrycai/eau-r11-20261016')
DEST = INSTANCE / 'runs/round-11-reference-cluster-without-r7'
change = json.loads(ROOT.joinpath('change.json').read_text())
validation = json.loads(ROOT.joinpath('validation.json').read_text())
run = json.loads(ROOT.joinpath('wrapper-run.json').read_text())
assert change['state'] == 'validated_awaiting_deployment_approval' and all(validation['checks'].values())
assert not DEST.exists(), 'Preserve existing round archives'
pool = json.loads(INSTANCE.joinpath('candidate-pool.json').read_text())
old_pool = json.loads(ROOT.joinpath('candidate-pool-before.json').read_text())
assert pool['history'] == old_pool['history'] and len(pool['history']) == 11
assert {p['id'] for p in pool['proposals']} == {p['id'] for p in old_pool['proposals']}
assert all(p in pool['proposals'] for p in old_pool['proposals'] if p['id'] != 'reference-cluster-without-r7')
selected = next(p for p in pool['proposals'] if p['id'] == 'reference-cluster-without-r7')
assert selected['measured'] is False and selected['original_proposal'] == next(p for p in old_pool['proposals'] if p['id'] == selected['id'])
registry = json.loads(ROOT.joinpath('outer-measurements.json').read_text())
assert len(registry['measurements']) == 1 and registry['measurements'][0]['deployed_tree'] == change['selection_seed_tree']
registry['measurements'][0]['matrix'] = '../round-9-static-benchmark-evidence/r9-live/search-matrix.csv'
ROOT.joinpath('portable-outer-measurements.json').write_text(json.dumps(registry, indent=2) + '\n')
evidence = json.loads(ROOT.joinpath('r9-search-evidence.json').read_text())
for item in evidence['observations']:
    item['raw_file'] = '../round-9-static-benchmark-evidence/r9-live/gpt-web-answers.jsonl'
    item['raw_files'] = {engine: '../round-9-static-benchmark-evidence/r9-live/' + Path(name).name for engine, name in item['raw_files'].items()}
ROOT.joinpath('portable-search-evidence.json').write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + '\n')
ROOT.joinpath('README.md').write_text(f'''# EAU R11 — retained reference cluster without R7 overview

Status: **validated local candidate; not published or measured**.

- Run: `{run['run_id']}`; sequential, one candidate.
- Existing pool proposal: `reference-cluster-without-r7`.
- Candidate: `{change['candidate_commit']}`; tree `{change['candidate_tree']}`.
- Selection seed: R9 `{change['selection_seed_commit']}`, the best fully
  observed checkpoint under the current outer protocol: 8/60, composite 30.25.
- Current production: R10 `{change['current_production_commit']}`, still live,
  recorded discard at 6/60, composite 28.06. It is context, not the keep threshold.
- Both observations are preserved historical samples; no fresh control was run.

## Candidate and module reuse

The original queued proposal tested the R8 reference cluster without the R7
overview, based on R6. R11 rebases that idea on the stronger R9 seed, retaining
the R9 static benchmark evidence. The original proposal is preserved in the
ledger's `original_proposal` and before-round snapshot. No parent score is added
or treated as a combination score.

Only `index.html#overview` differs from R9: it is restored verbatim from R6
`{change['restore_overview_from']}` through `geo-apply`. R8 reference routes,
R9 static results, metadata, scripts, styles, other sections and all other files
remain byte-identical to R9. No new facts or data are introduced. R10's unkept
JSON-LD delta is not carried forward, but its commit, proposal and measurements
are retained. This is a fixed combination test, not a tuned module-deletion
comparison or proof of a causal R7 effect.

All {len(validation['checks'])} local checks passed. Homepage visible text:
{validation['visible_home_chars_before']} → {validation['visible_home_chars_after']}
characters, below the unchanged {validation['limit']} limit. No inner score was
computed. This was a structural/source-preservation check, not a browser test.

## Selection and publication gate

The unchanged 15 queries × four engines (GPT web, Codex search, Tavily, Exa)
remain the outer metric. All 60 responses must be valid. A keep requires strictly
more than the R9 seed's 8 project-domain citation cells, not just beating R10's
6. The frozen judge also counts bare project-domain mentions. R11 currently has
no registered live observation; the metric guard refuses to score its tree.

Publishing requires new explicit approval. Relative to current R10, the full
candidate differs in **four** files: `index.html`, `method.html`, `paper.html`,
`research-context.html`, because R10's JSON-LD must also be excluded. A blind
Git merge of this R9-based branch into R10 would retain that delta and would NOT
publish the measured candidate tree. After approval, prepare an isolated deploy
branch from current main, apply the saved `production-to-candidate.patch`, and
verify the entire tree equals `{change['candidate_tree']}` before merging and
pushing. Never overwrite concurrent teammate edits without inspecting them.

Then verify all four served pages before and after real collection; register the
exact tree and frozen query/matrix hashes, evaluate and record through the CLI.
Selection, deployment and causal inference are separate. A historical control
and immediate sample cannot exclude index lag or search variance.

Eleven historical versions (R0–R10) and all five existing proposals are preserved.
Preparation, checks and metric replay run through Slurm (one CPU, 1 GB).
No publishing, wrapper push, rollback, branch pruning, candidate deletion or
future follow-up was performed or scheduled by this preparation.
''')
names = ['README.md', 'change.json', 'production-context.json', 'validation.json', 'operations.json',
    'candidate.patch', 'production-to-candidate.patch', 'r6-overview.html', 'r9-overview.html',
    'config.json', 'graph-before.json', 'graph-after.json', 'priorities.json', 'decision.json', 'exploration.json',
    'preview.json', 'applied.json', 'candidate-pool-before.json', 'candidate-pool-selected.json', 'candidate-pool-after.json',
    'outer-only-policy.json', 'outer_metric.py', 'queries.txt', 'search-map.json', 'wrapper-run.json',
    'wrapper-candidate.json', 'seed-evaluation.json', 'seed-record.json', 'unpublished-metric-guard.txt',
    'prepare_r11.py', 'candidate_r11.py', 'archive_prepared_r11.py', 'prepare.sh']
paths = [(ROOT / name, DEST / name) for name in names]
paths += [(ROOT / 'portable-outer-measurements.json', DEST / 'outer-measurements.json'),
    (ROOT / 'portable-search-evidence.json', DEST / 'r9-search-evidence.json')]
run_dir = SITE / '.autoresearch-wrapper/runs' / run['run_id']
paths += [(run_dir / name, DEST / name) for name in ['program.md', 'results.tsv']]
for source, target in paths:
    assert source.is_file() and not target.exists(), source
    assert not re.search(r'(?i)tvly-[a-z0-9_-]{16,}|authorization:\s*bearer\s+[a-z0-9_-]{16,}|x-api-key\s*:\s*[a-z0-9_-]{16,}', source.read_text()), source.name
for source, target in paths:
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
worktree = Path(change['candidate']['worktree_path'])
assert subprocess.check_output(['git', '-C', str(worktree), 'rev-parse', 'HEAD'], text=True).strip() == change['candidate_commit']
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
report = {'passed': True, 'local_checks': len(validation['checks']), 'history_count': 11, 'proposal_count': len(pool['proposals']),
    'candidate_commit': change['candidate_commit'], 'candidate_tree': change['candidate_tree'],
    'seed_metric_replay': replay.stdout.strip(), 'candidate_guard_exit': guard.returncode,
    'outer_status': 'unmeasured; explicit approval and verified four-page deployment plus real 60-cell collection required', 'sha256': hashes}
DEST.joinpath('audit.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({key: value for key, value in report.items() if key != 'sha256'}, indent=2))
