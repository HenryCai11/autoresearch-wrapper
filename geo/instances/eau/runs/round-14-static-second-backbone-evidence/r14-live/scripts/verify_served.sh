#!/bin/bash
set -euo pipefail
geo_r14_phase="${1:?before or after}"
case "$geo_r14_phase" in before|after) ;; *) exit 2 ;; esac
geo_r14_live=/scratch/henrycai/geo-runs/eau-r14-20261016/r14-live
geo_r14_site=/project/aip-xiye17/henrycai/eau-meta-agent.github.io
if [ "$geo_r14_phase" = after ]; then
  test "$(wc -l < "$geo_r14_live/gpt-web-answers.jsonl")" = 15
  test "$(wc -l < "$geo_r14_live/tavily-answers.jsonl")" = 15
  test "$(wc -l < "$geo_r14_live/exa-answers.jsonl")" = 15
  test "$(wc -l < "$geo_r14_live/codex-group-1/answers.jsonl")" = 8
  test "$(wc -l < "$geo_r14_live/codex-group-2/answers.jsonl")" = 7
  test -s "$geo_r14_live/codex-group-1/completed-at.txt"
  test -s "$geo_r14_live/codex-group-2/completed-at.txt"
fi
curl --fail --silent --show-error --max-time 45 --header 'Cache-Control: no-cache' \
  "https://eau-meta-agent.github.io/index.html?r14=fd5681c-$geo_r14_phase" \
  --output "$geo_r14_live/served-$geo_r14_phase/index.html"
cmp "$geo_r14_live/served-$geo_r14_phase/index.html" "$geo_r14_site/index.html"
test "$(git -C "$geo_r14_site" rev-parse HEAD^{tree})" = 1d987f64d620a79a9db3c354c50f89d4ce8ae164
git -C "$geo_r14_site" ls-remote origin refs/heads/main > "$geo_r14_live/origin-main-$geo_r14_phase.txt"
test "$(cut -f1 "$geo_r14_live/origin-main-$geo_r14_phase.txt")" = c762ead8370159e102c5ea11b1a43b944c71d1bf
date -u '+%Y-%m-%dT%H:%M:%SZ' > "$geo_r14_live/verified-$geo_r14_phase.txt"
sha256sum "$geo_r14_live/served-$geo_r14_phase/index.html"
echo "R14 homepage $geo_r14_phase verification passed"
