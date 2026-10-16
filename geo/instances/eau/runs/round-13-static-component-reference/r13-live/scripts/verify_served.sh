#!/bin/bash
set -euo pipefail
geo_r13_phase="${1:?before or after}"
case "$geo_r13_phase" in before|after) ;; *) exit 2 ;; esac
geo_r13_live=/scratch/henrycai/geo-runs/eau-r13-20261016/r13-live
geo_r13_site=/project/aip-xiye17/henrycai/eau-meta-agent.github.io
if [ "$geo_r13_phase" = after ]; then
  test "$(wc -l < "$geo_r13_live/gpt-web-answers.jsonl")" = 15
  test "$(wc -l < "$geo_r13_live/tavily-answers.jsonl")" = 15
  test "$(wc -l < "$geo_r13_live/exa-answers.jsonl")" = 15
  test "$(wc -l < "$geo_r13_live/codex-group-1/answers.jsonl")" = 8
  test "$(wc -l < "$geo_r13_live/codex-group-2/answers.jsonl")" = 7
  test -s "$geo_r13_live/codex-group-1/completed-at.txt"
  test -s "$geo_r13_live/codex-group-2/completed-at.txt"
fi
curl --fail --silent --show-error --max-time 45 --header 'Cache-Control: no-cache' \
  "https://eau-meta-agent.github.io/index.html?r13=fb91450-$geo_r13_phase" \
  --output "$geo_r13_live/served-$geo_r13_phase/index.html"
cmp "$geo_r13_live/served-$geo_r13_phase/index.html" "$geo_r13_site/index.html"
test "$(git -C "$geo_r13_site" rev-parse HEAD^{tree})" = 20f5afb5e7a68b3d66956e31dfad7ed4d8b15a6c
git -C "$geo_r13_site" ls-remote origin refs/heads/main > "$geo_r13_live/origin-main-$geo_r13_phase.txt"
test "$(cut -f1 "$geo_r13_live/origin-main-$geo_r13_phase.txt")" = c6fa063d86be9e1861b0d79c6d2f7e2c27e3c1aa
date -u '+%Y-%m-%dT%H:%M:%SZ' > "$geo_r13_live/verified-$geo_r13_phase.txt"
sha256sum "$geo_r13_live/served-$geo_r13_phase/index.html"
echo "R13 homepage $geo_r13_phase verification passed"
