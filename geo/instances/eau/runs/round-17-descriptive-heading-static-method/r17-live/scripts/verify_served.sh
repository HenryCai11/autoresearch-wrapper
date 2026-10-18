#!/bin/bash
set -euo pipefail
geo_r17_phase="${1:?before or after}"
case "$geo_r17_phase" in before|after) ;; *) exit 2 ;; esac
geo_r17_live=/scratch/henrycai/geo-runs/eau-r17-20261018/r17-live
geo_r17_site=/project/aip-xiye17/henrycai/eau-meta-agent.github.io
if [ "$geo_r17_phase" = after ]; then
  test "$(wc -l < "$geo_r17_live/gpt-web-answers.jsonl")" = 15
  test "$(wc -l < "$geo_r17_live/tavily-answers.jsonl")" = 15
  test "$(wc -l < "$geo_r17_live/exa-answers.jsonl")" = 15
  test "$(wc -l < "$geo_r17_live/codex-group-1/answers.jsonl")" = 8
  test "$(wc -l < "$geo_r17_live/codex-group-2/answers.jsonl")" = 7
  test -s "$geo_r17_live/codex-group-1/completed-at.txt"
  test -s "$geo_r17_live/codex-group-2/completed-at.txt"
fi
curl --fail --silent --show-error --max-time 45 --header 'Cache-Control: no-cache' \
  "https://eau-meta-agent.github.io/index.html?r17=dcf0b80-$geo_r17_phase" \
  --output "$geo_r17_live/served-$geo_r17_phase/index.html"
cmp "$geo_r17_live/served-$geo_r17_phase/index.html" "$geo_r17_site/index.html"
test "$(git -C "$geo_r17_site" rev-parse HEAD^{tree})" = acbe04ac17e69189e3eb630ed9c89e449b8faa44
git -C "$geo_r17_site" ls-remote origin refs/heads/main > "$geo_r17_live/origin-main-$geo_r17_phase.txt"
test "$(cut -f1 "$geo_r17_live/origin-main-$geo_r17_phase.txt")" = 6eb91c2d44003afe248e5e2623a2a6a2f38f5675
date -u '+%Y-%m-%dT%H:%M:%SZ' > "$geo_r17_live/verified-$geo_r17_phase.txt"
sha256sum "$geo_r17_live/served-$geo_r17_phase/index.html"
echo "R17 homepage $geo_r17_phase verification passed"
