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
