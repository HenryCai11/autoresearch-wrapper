#!/bin/bash
set -euo pipefail
geo_r15_phase="${1:?before or after}"
case "$geo_r15_phase" in before|after) ;; *) exit 2 ;; esac
geo_r15_live=/scratch/henrycai/geo-runs/eau-r15-20261017/r15-live
geo_r15_site=/project/aip-xiye17/henrycai/eau-meta-agent.github.io
if [ "$geo_r15_phase" = after ]; then
  test "$(wc -l < "$geo_r15_live/gpt-web-answers.jsonl")" = 15
  test "$(wc -l < "$geo_r15_live/tavily-answers.jsonl")" = 15
  test "$(wc -l < "$geo_r15_live/exa-answers.jsonl")" = 15
  test "$(wc -l < "$geo_r15_live/codex-group-1/answers.jsonl")" = 8
  test "$(wc -l < "$geo_r15_live/codex-group-2/answers.jsonl")" = 7
  test -s "$geo_r15_live/codex-group-1/completed-at.txt"
  test -s "$geo_r15_live/codex-group-2/completed-at.txt"
fi
curl --fail --silent --show-error --max-time 45 --header 'Cache-Control: no-cache' \
  "https://eau-meta-agent.github.io/index.html?r15=ca89362-$geo_r15_phase" \
  --output "$geo_r15_live/served-$geo_r15_phase/index.html"
cmp "$geo_r15_live/served-$geo_r15_phase/index.html" "$geo_r15_site/index.html"
test "$(git -C "$geo_r15_site" rev-parse HEAD^{tree})" = 13982678cdeb9efc1bb4ea871f6f150a9a5f16ce
git -C "$geo_r15_site" ls-remote origin refs/heads/main > "$geo_r15_live/origin-main-$geo_r15_phase.txt"
test "$(cut -f1 "$geo_r15_live/origin-main-$geo_r15_phase.txt")" = 596ccda6c33a4bb2ea9cac3daa7d489e856f264d
date -u '+%Y-%m-%dT%H:%M:%SZ' > "$geo_r15_live/verified-$geo_r15_phase.txt"
sha256sum "$geo_r15_live/served-$geo_r15_phase/index.html"
echo "R15 homepage $geo_r15_phase verification passed"
