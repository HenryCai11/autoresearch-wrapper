# Instance: henrycai11.github.io

Min Cai's academic homepage (Jekyll on GitHub Pages; site repo `/scratch/henrycai/HenryCai11.github.io`, deploys from `master`). Data and config only:

- `map.json`: knowledge map, with facts taken from the site and confirmed by Min Cai (location: Edmonton)
- `instance.env`: site paths, builder, editable files, GoatCounter code
- `probes.jsonl`: search probes; `ood.jsonl`: GoatCounter snapshots

## Baseline (2026-10-15, master @ 7f95245)

| signal | value |
| --- | --- |
| METRIC | 71.77 |
| matrix (offline columns) | 50.0: every keyword is on the site, none in JSON-LD, no `llms.txt` |
| technical | 46.67: no Person/ScholarlyArticle JSON-LD, no `llms.txt`, placeholder meta description ("personal description"), no canonical/OG tags, template sample publications still built |
| LLM comprehension | 94.87: one miss (DataSciBench venue answered as "ICLR 2025": venue labels and titles are ambiguous in plain text) |
| search probes | 2/22 found (TDRM, MGS); name queries find nothing; papers name "Cai" without affiliation |
| traffic (7 days) | 1 visit, 0 AI-referred |
| homepage visible text | 3041 chars (limit set to 3950) |

## Round 1 (2026-10-15, site branch `geo/round-1`)

Sequential optimize run on `_pages/about.md`, 7 candidates, all kept; ended early once the local score hit its ceiling. Per-round data: `runs/round-1-frontier.json`. Dashboard: https://claude.ai/artifact/JhBDVhn6q2SAgQwyMYkQ1K

| round | change | METRIC |
| --- | --- | --- |
| 0 | baseline | 71.77 |
| 1 | real site description, drop template paper pages, location in config | 73.52 |
| 2 | JSON-LD Person | 81.28 |
| 3 | JSON-LD ScholarlyArticle for 9 papers | 86.23 |
| 4 | `llms.txt` | 96.05 |
| 5 | canonical + Open Graph/Twitter tags | 98.55 |
| 6 | exclude `_publications` template samples | 99.05 |
| 7 | JSON-LD colleagues and internships | 100.00 |

Staged (not committed) in the site checkout: `_config.yml`, `_includes/geo-head.html` (new), `_layouts/default.html`, `llms.txt` (new). Live search probes and traffic need a deploy, then a re-probe after recrawl.
