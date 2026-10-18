#!/bin/bash
set -euo pipefail
geo_r16_phase="${1:?before or after}"
case "$geo_r16_phase" in before|after) ;; *) exit 2 ;; esac
geo_r16_live=/scratch/henrycai/geo-runs/eau-r16-20261017/r16-live
geo_r16_site=/project/aip-xiye17/henrycai/eau-meta-agent.github.io
if [ "$geo_r16_phase" = after ]; then
  test "$(wc -l < "$geo_r16_live/gpt-web-answers.jsonl")" = 15
  test "$(wc -l < "$geo_r16_live/tavily-answers.jsonl")" = 15
  test "$(wc -l < "$geo_r16_live/exa-answers.jsonl")" = 15
  test "$(wc -l < "$geo_r16_live/codex-group-1/answers.jsonl")" = 8
  test "$(wc -l < "$geo_r16_live/codex-group-2/answers.jsonl")" = 7
  test -s "$geo_r16_live/codex-group-1/completed-at.txt"
  test -s "$geo_r16_live/codex-group-2/completed-at.txt"
fi
curl --fail --silent --show-error --max-time 45 --header 'Cache-Control: no-cache' \
  "https://eau-meta-agent.github.io/index.html?r16=18c0ae3-$geo_r16_phase" \
  --output "$geo_r16_live/served-$geo_r16_phase/index.html"
cmp "$geo_r16_live/served-$geo_r16_phase/index.html" "$geo_r16_site/index.html"
test "$(git -C "$geo_r16_site" rev-parse HEAD^{tree})" = 692b95a10e27de1e9c84011fb839cba3b0eb6b15
git -C "$geo_r16_site" ls-remote origin refs/heads/main > "$geo_r16_live/origin-main-$geo_r16_phase.txt"
test "$(cut -f1 "$geo_r16_live/origin-main-$geo_r16_phase.txt")" = ff79a10c4e93906cad803be5e23580f60bd98412
date -u '+%Y-%m-%dT%H:%M:%SZ' > "$geo_r16_live/verified-$geo_r16_phase.txt"
sha256sum "$geo_r16_live/served-$geo_r16_phase/index.html"
echo "R16 homepage $geo_r16_phase verification passed"
