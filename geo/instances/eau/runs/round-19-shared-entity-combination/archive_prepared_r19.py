"""Durably preserve the new unmeasured combination and all old evidence."""
import re
import shutil
import sys
from common import *

assert os.environ.get('SLURM_JOB_ID')
assert not DEST.exists(), 'Append-only archive refuses overwrite'
change = json.loads(ROOT.joinpath('change.json').read_text())
validation = json.loads(ROOT.joinpath('validation.json').read_text())
run = json.loads(ROOT.joinpath('wrapper-run.json').read_text())
pool = json.loads(INSTANCE.joinpath('candidate-pool.json').read_text())
before = json.loads(ROOT.joinpath('candidate-pool-before.json').read_text())
assert change['state'] == 'validated_awaiting_deployment_approval' and all(validation['checks'].values())
assert pool['history'] == before['history'] and len(pool['history']) == 19
assert all(h['retain_for_combinations'] for h in pool['history'])
assert pool['best_observed'] == before['best_observed'] and pool['best_observed']['round'] == 18
assert len(pool['proposals']) == 13 and len(before['proposals']) == 12
assert all(p in pool['proposals'] for p in before['proposals'])
selected = next(p for p in pool['proposals'] if p['id'] == SELECTED)
assert selected['parents'] == ['r18','r10'] and selected['measured'] is False and 'outer_observation' not in selected
assert {p['id'] for p in pool['proposals'] if not p.get('measured',False)} == {SELECTED,'external-paper-link-audit'}
assert next(p for p in pool['proposals'] if p['id'] == 'shared-scholarly-entity')['status'] == 'discard'
assert git(PRODUCTION,'rev-parse','HEAD') == change['current_production_commit'] and not git(PRODUCTION,'status','--porcelain')
registry = json.loads(ROOT.joinpath('outer-measurements.json').read_text())
assert len(registry['measurements']) == 1 and registry['measurements'][0]['label'] == 'r18-best-reused-control'
registry['measurements'][0]['matrix'] = '../round-18-alphaxiv-paper-routing/r18-live/search-matrix.csv'
write('portable-outer-measurements.json',registry)
evidence = json.loads(ROOT.joinpath('r18-search-evidence.json').read_text())
for item in evidence['observations']:
    item['raw_file'] = '../round-18-alphaxiv-paper-routing/r18-live/gpt-web-answers.jsonl'
    item['raw_files'] = {engine:'../round-18-alphaxiv-paper-routing/r18-live/' + Path(name).name for engine,name in item['raw_files'].items()}
write('portable-search-evidence.json',evidence)
ROOT.joinpath('README.md').write_text(f'''# EAU R19 — retained shared-entity metadata on R18

Status: **validated local candidate; not published or measured**.

- Run: {run['run_id']}; sequential, one four-file metadata candidate.
- Candidate: {change['candidate_commit']}.
- Tree: {change['candidate_tree']}.
- Seed: best complete measured R18 {change['selection_seed_commit']}.
- Primary control: 12/60 citations, 20.00/100; secondary composite 35.19444.
- Production remains unchanged R18 {change['current_production_commit']}.
- Keep requires all 60 valid and strictly more than 12/60; ties discard.

## Why revisit a retained candidate

R18 returned explicit project URLs in eleven cells, including five support-page
URL cells: paper.html in three exact-query cells, method.html in one fuzzy cell,
and research-context.html in another fuzzy cell. These are actual saved Exa
source URLs, not inferred graph reach. See observed-entry-surfaces.json and
the linked original R18 raw answers in r18-search-evidence.json.

R19 retests the exact final R10 shared-paper metadata scheme on the current
R18 tree. Each document has one page-specific WebPage and one identical
ScholarlyArticle with @id https://eau-meta-agent.github.io/#paper; each page's
mainEntity references that paper. Titles, topic metadata and descriptions remain
page-specific. This is an identity/relationship experiment on an observed
cross-page entry surface, not a prediction of retrieval or citation lift.

R10 previously measured 6/60 against historical R9 8/60 and remains a discard.
Its old result is untouched. R19 has parents R18 and R10 and will receive a
separate observation. Neither R10's score nor R18's score is added or averaged
to forecast it. module-review.json reviews all ten modules and every retained
proposal, including unselected H1, table, overview and external-link alternatives.

## Exact replay, not a rewrite of the archived proposal

The four replacement blocks come from the final measured R10 commit
04e7ea4d0b1a6be0c65301c2a297e401294a0b78 and match schema-after.json.
The final homepage operation also matches the corrected archived operations.json.
Failed initial R10 attempts are not replayed. The old R9→R10 complete HTML
for all four files was reproduced with only those schema blocks, and R18's
original blocks match that old R9 input exactly. Parent hashes and provenance
are recorded under parents/ and combination-source.json.

Only four JSON-LD blocks differ from R18. All non-JSON-LD bytes, body HTML,
visible text, H1/H2 headings, method reference, result evidence, canonical
links, citation/PDF fields, BibTeX and all alphaXiv reading anchors are unchanged.
README, llms.txt and site-config.js retain R18's alphaXiv destinations.
Scripts, styles, assets, robots and sitemap are unchanged. No new scientific
claim, author, affiliation, year, result or topic was invented; the article facts
and page fields are checked against the existing R10 contract and R18 data.

One homepage meta:schema operation used geo-apply. Three exact support-page
replacements used apply_patch inside the allocated worktree because the existing
graph does not expose them as mutable text-file nodes. There is no wrapper-core
extension or claim of full support-file graph coverage. The complete manifest,
both subsets, patches and candidate snapshots are durably archived.

## Validation, retained history and publication gate

All {len(validation['checks'])} structural/factual checks passed. Visible homepage text:
{validation['visible_home_chars_before']} → {validation['visible_home_chars_after']} characters,
below the unchanged {validation['limit']} limit. Checks cover exact parent replay,
reversal to R18, shared/per-page identity, title/topic/author/year preservation,
all nine R18 routing operations, links/IDs, hidden text and frozen
map/query/judge/normalizer/settings/control fingerprints. No inner score was
computed. No browser/visual test was performed; unchanged body/scripts/styles
are not described as a browser test. Technical references for the relationships
are [mainEntity](https://schema.org/mainEntity),
[mainEntityOfPage](https://schema.org/mainEntityOfPage), and
[JSON-LD node identifiers](https://www.w3.org/TR/json-ld11/#node-identifiers).

All nineteen R0–R18 observations, twelve older proposals and best_observed R18
remain unchanged. The thirteenth proposal is separate. Only R19 and the
external-authority proposal are unmeasured. Existing candidates remain available
for future combinations; this is an agent-maintained ledger, not a scheduler.

The exact-tree metric rejects R19 until explicitly approved publication and
real live collection. Recheck then-current main, verify the complete candidate
tree and all four changed served HTML resources before and after all requests.
Use the frozen 15 queries × GPT web / Codex / Tavily / Exa; no memory dimension.
R18 is a historical control, not a fresh simultaneous measurement. The copied
settings file retains legacy R9 baseline wording; the actual registered control
is R18. Bare project-domain citations and explicit source URLs remain distinct.
alphaXiv/arXiv URLs are not project citations, and alphaXiv traffic is unmeasured.
Immediate historical-control observations cannot establish causal module effects.

Python, wrapper CLI, seed replay and validation used Slurm (one CPU, 1 GB).
No site publication/push, new paid searches, rollback, pruning, deletion,
automatic follow-up or next-round start was performed.
''')
names = ['README.md','change.json','production-context.json','validation.json','schema-after.json',
    'combination-source.json','observed-entry-surfaces.json','new-proposals.json','collection-settings.json',
    'operations.json','wrapper-operations.json','manual-operations.json','candidate.patch','production-to-candidate.patch',
    'module-review.json','config.json','graph-before.json','graph-after.json','priorities.json','decision.json',
    'exploration.json','preview.json','applied.json','candidate-pool-before.json','candidate-pool-selected.json',
    'candidate-pool-after.json','outer-only-policy.json','outer_metric.py','queries.txt','search-map.json',
    'wrapper-run.json','wrapper-candidate.json','seed-evaluation.json','seed-record.json','unpublished-metric-guard.txt',
    'common.py','prepare_r19.py','allocate_r19.py','candidate_r19.py','archive_prepared_r19.py',
    'select_candidate.sh','allocate_candidate.sh','prepare_candidate.sh','r18-production-index.html']
names += [p.relative_to(ROOT).as_posix() for p in sorted(ROOT.joinpath('parents').iterdir())]
names += ['served-r18/' + name for name in FILES]
paths = [(ROOT / name,DEST / name) for name in names]
paths += [(ROOT / 'portable-outer-measurements.json',DEST / 'outer-measurements.json'),
    (ROOT / 'portable-search-evidence.json',DEST / 'r18-search-evidence.json')]
run_dir = SITE / '.autoresearch-wrapper/runs' / run['run_id']
paths += [(run_dir / name,DEST / name) for name in ['program.md','results.tsv']]
worktree = Path(change['candidate']['worktree_path'])
paths += [(worktree / name,DEST / 'site' / name) for name in FILES]
for source,target in paths:
    assert source.is_file() and not target.exists(), source
    assert not re.search(r'(?i)tvly-[a-z0-9_-]{16,}|authorization:\s*bearer\s+[a-z0-9_-]{16,}|x-api-key\s*:\s*[a-z0-9_-]{16,}',source.read_text()),source.name
for source,target in paths:
    target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(source,target)
assert not git(worktree,'status','--porcelain')
seed = subprocess.run([sys.executable,str(DEST / 'outer_metric.py')],cwd=worktree.parent / 'seed',check=True,capture_output=True,text=True)
assert 'LIVE_PROJECT_CITATIONS=12/60' in seed.stdout and 'METRIC=20.0' in seed.stdout
guard = subprocess.run([sys.executable,str(DEST / 'outer_metric.py')],cwd=worktree,capture_output=True,text=True)
assert guard.returncode == 2 and 'No live measurement' in guard.stderr
DEST.joinpath('wrapper-status.json').write_text(cli('status','--json',name='wrapper-status.json'))
hashes = {p.relative_to(DEST).as_posix():digest(p) for p in sorted(DEST.rglob('*')) if p.is_file()}
audit = {'passed':True,'local_checks':len(validation['checks']),'history_count':19,'old_proposals_preserved':12,
    'proposal_count':13,'unmeasured_proposals':2,'candidate_commit':change['candidate_commit'],
    'candidate_tree':change['candidate_tree'],'applied_schema_operations':4,'wrapper_operations':1,'manual_operations':3,
    'seed_metric_replay':seed.stdout.strip(),'candidate_guard_exit':guard.returncode,
    'outer_status':'Unmeasured R19; explicit approval, exact deployment and complete real live collection required',
    'sha256':hashes}
DEST.joinpath('audit.json').write_text(json.dumps(audit,indent=2) + '\n')
print(json.dumps({k:v for k,v in audit.items() if k != 'sha256'},indent=2))
