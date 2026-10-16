"""Append an unmeasured R10 candidate without replacing R9 or pool history."""
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
INSTANCE = Path('/project/aip-xiye17/henrycai/autoresearch-wrapper/geo/instances/eau')
DEST = INSTANCE / 'runs/round-10-shared-scholarly-entity'
change = json.loads(ROOT.joinpath('change.json').read_text())
validation = json.loads(ROOT.joinpath('validation.json').read_text())
run = json.loads(ROOT.joinpath('wrapper-run.json').read_text())
assert change['state'] == 'validated_awaiting_deployment_approval'
assert all(validation['checks'].values())
assert not DEST.exists()
registry = json.loads(ROOT.joinpath('outer-measurements.json').read_text())
registry['measurements'][0]['matrix'] = '../round-9-static-benchmark-evidence/r9-live/search-matrix.csv'
ROOT.joinpath('portable-outer-measurements.json').write_text(json.dumps(registry, indent=2) + '\n')
evidence = json.loads(ROOT.joinpath('r9-search-evidence.json').read_text())
for item in evidence['observations']:
    item['raw_file'] = '../round-9-static-benchmark-evidence/r9-live/gpt-web-answers.jsonl'
    item['raw_files'] = {engine: '../round-9-static-benchmark-evidence/r9-live/' + Path(name).name for engine, name in item['raw_files'].items()}
ROOT.joinpath('portable-search-evidence.json').write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + '\n')
ROOT.joinpath('README.md').write_text(f'''# EAU R10 — shared scholarly identity

Status: **validated local candidate, not published or measured**.

- Run: `{run['run_id']}`; sequential, one candidate.
- Existing pool proposal: `shared-scholarly-entity`; round change: `r10-shared-scholarly-entity`.
- Base production: `{change['base_production_commit']}` (R9).
- Candidate: `{change['candidate_commit']}`; tree `{change['candidate_tree']}`.
- Outer-only primary: fixed four-engine project-domain citation rate, maximize.
- Baseline: preserved [R9 live record](../round-9-static-benchmark-evidence/r9-live/REPORT.md),
  8/60 citations, composite 30.25, all 60 valid; not a newly collected R10 control.

## Dependency-aware intervention

R9 produced five explicit homepage URLs but no support-page URLs. All four local
pages describe the same paper as anonymous ScholarlyArticle objects with different
page URLs and no shared @id. R10 selects an existing queued proposal to distinguish
the paper from its project/reference pages. This is not predicted search lift.

| Module | Role in R10 | Changed? |
| --- | --- | --- |
| `index.html` JSON-LD | Shared paper identity and distinct homepage WebPage | Yes |
| `paper.html` JSON-LD | Same paper identity and distinct bibliographic WebPage | Yes |
| `method.html`, `research-context.html` JSON-LD | Same paper identity and separate reference WebPages | Yes |
| All visible content, R8 reference routes and R9 static results | Retained byte-for-byte | No |
| Scripts, styles, crawler files and text summary | Retained byte-for-byte | No |

Each document contains a WebPage node whose mainEntity references
`https://eau-meta-agent.github.io/#paper`, and the identical ScholarlyArticle
record references the canonical homepage through mainEntityOfPage. Existing
page-specific descriptions/topics/keywords remain attached to their WebPage;
existing homepage paper facts are preserved, with headline/date copied from the
existing paper record. No new authors, affiliations, dates or results are invented.

Only the JSON-LD block in each page changed. The homepage uses `geo-apply` on
`meta:schema`; linked HTML asset nodes currently do not support `replace_text`,
so the other three blocks were changed with an exact generated `apply_patch`.
See `edit-mechanism.json`; wrapper-core code and canonical state were not edited
by hand. All body bytes and non-JSON-LD head bytes are unchanged. Visible text:
{validation['visible_home_chars_before']} to {validation['visible_home_chars_after']}
characters (unchanged), below the existing limit of {validation['limit']}.
No inner score was computed. All {len(validation['checks'])} local checks passed.
Checks cover JSON syntax, identities, references and source preservation; they
are not a full RDF expansion, browser test or search-engine rich-result test.

Technical basis: [Schema.org mainEntity](https://schema.org/mainEntity),
[mainEntityOfPage](https://schema.org/mainEntityOfPage), and
[W3C JSON-LD node identifiers](https://www.w3.org/TR/json-ld11/#node-identifiers).
These document the representation, not an expected search-engine ranking benefit.

## Retention and next gate

Before/after [candidate ledger](../../candidate-pool.json) snapshots are retained
here. Ten historical versions and all five existing proposals remain available;
R10 is unmeasured and has no assigned outer score. Queued combinations are not
ranked by adding historical metrics.

Preparation and validation run through Slurm with one CPU and 1 GB memory.
No installation or Python computation was performed on the login node.

After explicit R10 publication approval, verify all four changed resources against
this candidate, then collect the unchanged 15 queries × four engines. Register
only complete real observations for the exact deployed Git tree before the
wrapper evaluates and records the candidate. Preserve the baseline, failures
and timestamps. An immediate observation cannot establish a causal lift or
exclude indexing lag. No future follow-up or rollback has been scheduled.
''')
names = ['README.md', 'change.json', 'validation.json', 'operations.json', 'candidate.patch',
         'config.json', 'graph-before.json', 'graph-after.json', 'priorities.json', 'decision.json', 'exploration.json',
         'preview.json', 'applied.json', 'schema-before.json', 'schema-after.json', 'schema-contract.json', 'edit-mechanism.json',
         'validation-attempt-1.json', 'prepare-1794026.out', 'validate-1794060.out',
         'prepare_r10.py', 'allocate_r10.py', 'validate_r10.py', 'archive_prepared_r10.py', 'prepare.sh', 'validate.sh',
         'candidate-pool-before.json', 'candidate-pool-selected.json', 'candidate-pool-after.json',
         'outer-only-policy.json', 'outer_metric.py', 'queries.txt', 'search-map.json',
         'wrapper-run.json', 'wrapper-candidate.json', 'seed-evaluation.json', 'seed-record.json', 'unpublished-metric-guard.txt']
paths = [(ROOT / name, DEST / name) for name in names]
paths += [(ROOT / 'portable-outer-measurements.json', DEST / 'outer-measurements.json'),
          (ROOT / 'portable-search-evidence.json', DEST / 'r9-search-evidence.json')]
run_dir = Path('/scratch/henrycai/eau-r10-20261016/.autoresearch-wrapper/runs') / run['run_id']
paths += [(run_dir / name, DEST / name) for name in ['program.md', 'results.tsv']]
for source, target in paths:
    assert source.is_file() and not target.exists(), target
    assert not re.search(r'(?i)tvly-[a-z0-9_-]{16,}|authorization:\s*bearer\s+[a-z0-9_-]{16,}|x-api-key\s*:\s*[a-z0-9_-]{16,}', source.read_text()), source.name
for source, target in paths:
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
print(json.dumps({'archive': str(DEST), 'candidate_commit': change['candidate_commit'],
                  'validation_passed': True, 'outer_metric': 'unmeasured',
                  'scope': change['files']}, indent=2))
