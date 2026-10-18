"""Append-only durable archive; retain all observations and old candidates."""
import re
import shutil
import sys
from common import *

assert os.environ.get('SLURM_JOB_ID')
change = json.loads(ROOT.joinpath('change.json').read_text())
validation = json.loads(ROOT.joinpath('validation.json').read_text())
run = json.loads(ROOT.joinpath('wrapper-run.json').read_text())
pool = json.loads(INSTANCE.joinpath('candidate-pool.json').read_text())
before = json.loads(ROOT.joinpath('candidate-pool-before.json').read_text())
assert change['state'] == 'validated_awaiting_deployment_approval' and all(validation['checks'].values())
assert not DEST.exists(), 'Append-only archive refuses overwrite'
assert pool['history'] == before['history'] and len(pool['history']) == 18
assert all(entry['retain_for_combinations'] for entry in pool['history'])
assert pool['best_observed'] == before['best_observed'] and pool['best_observed']['round'] == 17
assert all(proposal in pool['proposals'] for proposal in before['proposals'])
assert len(before['proposals']) == 11 and len(pool['proposals']) == 12
assert {p['id'] for p in pool['proposals']} - {p['id'] for p in before['proposals']} == {SELECTED}
selected = next(p for p in pool['proposals'] if p['id'] == SELECTED)
assert selected['parents'] == ['r17'] and selected['measured'] is False and 'outer_observation' not in selected
assert len([p for p in pool['proposals'] if not p.get('measured', False)]) == 2
assert git(PRODUCTION, 'rev-parse', 'HEAD') == change['current_production_commit']
assert not git(PRODUCTION, 'status', '--porcelain')
registry = json.loads(ROOT.joinpath('outer-measurements.json').read_text())
assert len(registry['measurements']) == 1
registry['measurements'][0]['matrix'] = '../round-17-descriptive-heading-static-method/r17-live/search-matrix.csv'
write('portable-outer-measurements.json', registry)
evidence = json.loads(ROOT.joinpath('r17-search-evidence.json').read_text())
for item in evidence['observations']:
    item['raw_file'] = '../round-17-descriptive-heading-static-method/r17-live/gpt-web-answers.jsonl'
    item['raw_files'] = {engine: '../round-17-descriptive-heading-static-method/r17-live/' + Path(name).name
                         for engine,name in item['raw_files'].items()}
write('portable-search-evidence.json', evidence)
ROOT.joinpath('README.md').write_text(f'''# EAU R18 — alphaXiv paper-reading routes

Status: **validated local candidate; not published or measured**.

- Run: {run['run_id']}; sequential, one seven-file routing bundle.
- Candidate: {change['candidate_commit']}.
- Tree: {change['candidate_tree']}.
- Seed: best fully measured R17 {change['selection_seed_commit']},
  10/60 citations, composite 34.30556; kept against historical R16 9/60.
- Production remains R17 {change['current_production_commit']}, unchanged.
- Keep requires strictly more than 10/60 with all 60 responses valid; ties discard.

## User-requested traffic routing, not invented GEO lift

All six static HTML paper-reading anchors now point to
https://www.alphaxiv.org/abs/2610.16523, with matching alphaXiv labels.
The website README Paper entry, llms.txt Paper entry, and site-config.js
paperUrl agree with that destination. This is exactly nine replacements in
seven files, not an additional content-optimization bundle.

The public alphaXiv page returned HTTP 200. Its title, canonical URL and
citation_arxiv_id match EAU and 2610.16523. alphaxiv-verification.json preserves
that minimal identity evidence and the fetched body's SHA-256. Full third-party
HTML remains scratch-only; no external page, account or backlink was edited.

arXiv remains the scholarly identifier/source. All four HTML heads, JSON-LD
sameAs identities, canonical project URLs, arXiv PDF metadata, CITATION.cff and
the two BibTeX blocks are byte-unchanged. Those citation fields are not
paper-reading buttons. All project-site self-links remain unchanged.

There is no alphaXiv click/visit measurement or new tracking. Sending future
clicks there is the requested behavior; a traffic increase is not claimed.
The frozen metric still counts only the project domain, not alphaXiv or arXiv.
No discovery improvement is assumed from replacing the outbound URL.

## Scope, graph limits and retained candidates

module-review.json reviews all ten modules. R17's static method reference,
both R16 H2s, R7 overview, R8 routes, R9 default results and all factual claims
remain. No R12 H1 or R14 second-backbone table is inherited. Scripts, styles,
crawler files and assets are unchanged except the paperUrl configuration value.
Full changes are in candidate.patch and production-to-candidate.patch;
site/ contains snapshots of the seven candidate files.

The existing geo-graph exposes only index.html, README.md and site-config.js
for this bundle. Five replacements used geo-apply on those supported nodes;
four replacements in support HTML and llms.txt used apply_patch inside the
allocated worktree. Both subsets and the complete manifest are archived.
No wrapper-core change or full support-file graph coverage is implied.
Saved actual R17 search-source URLs feed the graph decision/exploration tools;
they are not new searches or a ranking claim for this user-selected candidate.

All eighteen R0–R17 observations, eleven old proposals and best_observed R17
remain unchanged. A twelfth proposal identifies R18 separately, with parent R17.
Only R18 and the authority-gated external-paper proposal are unmeasured.
Prior candidates remain available for combinations without adding their scores.
This is an agent-maintained ledger, not a recombination scheduler.

## Validation and publication gate

All {len(validation['checks'])} structural/factual checks passed. Visible homepage:
{validation['visible_home_chars_before']} → {validation['visible_home_chars_after']}
characters, below the unchanged {validation['limit']} limit. Checks cover exact
operation replay and reversal, six aligned anchors, consistent configuration,
unchanged scholarly metadata/BibTeX, R17 method/results retention, local links,
unique IDs, hidden text and frozen map/query/judge/normalizer/settings/control.
No inner score or browser/visual test was performed. Static validation does not
establish rendered fit or browser navigation behavior.

The exact-tree metric refuses this unpublished candidate. Separate explicit
R18 publication approval is required. Recheck then-current main for teammate
changes, deploy the complete candidate tree, and verify all seven changed
served resources before and after real requests. Do not check only index.html.

After approval, use the frozen 15 queries × GPT web / Codex / Tavily / Exa;
no memory-model dimension. All 60 cells must be valid and citations must exceed
the historical R17 10/60 control for keep. Secondary composite is report-only.
The unchanged judge also counts bare project-domain occurrences, so explicit
source URLs are reported separately. Immediate samples and historical controls
do not establish causal lift or exclude indexing lag. No follow-up is scheduled.

Preparation, seed replay and validation used Slurm, one CPU and 1 GB.
No site publication/push, new paid eval search, rollback, pruning or candidate
deletion was performed. Durable patches, manifests and snapshots live in project
storage; scratch is not the only copy.
''')
names = ['README.md', 'change.json', 'production-context.json', 'validation.json',
    'alphaxiv-verification.json', 'new-proposals.json', 'collection-settings.json',
    'operations.json', 'wrapper-operations.json', 'manual-operations.json',
    'candidate.patch', 'production-to-candidate.patch', 'module-review.json',
    'config.json', 'graph-before.json', 'graph-after.json', 'priorities.json', 'decision.json',
    'exploration.json', 'preview.json', 'applied.json', 'candidate-pool-before.json',
    'candidate-pool-selected.json', 'candidate-pool-after.json', 'outer-only-policy.json',
    'outer_metric.py', 'queries.txt', 'search-map.json', 'wrapper-run.json', 'wrapper-candidate.json',
    'seed-evaluation.json', 'seed-record.json', 'unpublished-metric-guard.txt', 'common.py',
    'prepare_r18.py', 'allocate_r18.py', 'candidate_r18.py', 'archive_prepared_r18.py',
    'select_candidate.sh', 'allocate_candidate.sh', 'prepare_candidate.sh', 'r17-production-index.html']
paths = [(ROOT / name, DEST / name) for name in names]
paths += [(ROOT / 'portable-outer-measurements.json', DEST / 'outer-measurements.json'),
          (ROOT / 'portable-search-evidence.json', DEST / 'r17-search-evidence.json')]
run_dir = SITE / '.autoresearch-wrapper/runs' / run['run_id']
paths += [(run_dir / name, DEST / name) for name in ['program.md', 'results.tsv']]
worktree = Path(change['candidate']['worktree_path'])
paths += [(worktree / name, DEST / 'site' / name) for name in FILES]
for source,target in paths:
    assert source.is_file() and not target.exists(), source
    assert not re.search(r'(?i)tvly-[a-z0-9_-]{16,}|authorization:\s*bearer\s+[a-z0-9_-]{16,}|x-api-key\s*:\s*[a-z0-9_-]{16,}', source.read_text()), source.name
for source,target in paths:
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
assert not git(worktree, 'status', '--porcelain')
replay = subprocess.run([sys.executable, str(DEST / 'outer_metric.py')], cwd=worktree.parent / 'seed',
                         check=True, capture_output=True, text=True)
assert 'LIVE_PROJECT_CITATIONS=10/60' in replay.stdout
guard = subprocess.run([sys.executable, str(DEST / 'outer_metric.py')], cwd=worktree, capture_output=True, text=True)
assert guard.returncode == 2 and 'No live measurement' in guard.stderr
DEST.joinpath('wrapper-status.json').write_text(cli('status', '--json', name='wrapper-status.json'))
hashes = {path.relative_to(DEST).as_posix(): digest(path) for path in sorted(DEST.rglob('*')) if path.is_file()}
audit = {'passed': True, 'local_checks': len(validation['checks']), 'history_count': 18,
    'old_proposals_preserved': 11, 'proposal_count': 12, 'unmeasured_proposals': 2,
    'candidate_commit': change['candidate_commit'], 'candidate_tree': change['candidate_tree'],
    'applied_operations': 9, 'wrapper_operations': 5, 'manual_operations': 4,
    'seed_metric_replay': replay.stdout.strip(), 'candidate_guard_exit': guard.returncode,
    'outer_status': 'Unmeasured R18; explicit publication approval and complete real live collection required',
    'traffic_status': 'alphaXiv clicks/visits not measured', 'sha256': hashes}
DEST.joinpath('audit.json').write_text(json.dumps(audit, indent=2) + '\n')
print(json.dumps({key:value for key,value in audit.items() if key != 'sha256'}, indent=2))
