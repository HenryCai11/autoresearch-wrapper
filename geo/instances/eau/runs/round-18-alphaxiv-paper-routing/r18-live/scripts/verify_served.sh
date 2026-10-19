#!/bin/bash
set -euo pipefail
geo_r18_phase="${1:?before or after}"
case "$geo_r18_phase" in before|after) ;; *) exit 2 ;; esac
geo_r18_live=/scratch/henrycai/geo-runs/eau-r18-20261018/r18-live
geo_r18_site=/project/aip-xiye17/henrycai/eau-meta-agent.github.io
if [ "$geo_r18_phase" = after ]; then
  test "$(wc -l < "$geo_r18_live/gpt-web-answers.jsonl")" = 15
  test "$(wc -l < "$geo_r18_live/tavily-answers.jsonl")" = 15
  test "$(wc -l < "$geo_r18_live/exa-answers.jsonl")" = 15
  test "$(wc -l < "$geo_r18_live/codex-group-1/answers.jsonl")" = 8
  test "$(wc -l < "$geo_r18_live/codex-group-2/answers.jsonl")" = 7
  test -s "$geo_r18_live/codex-group-1/completed-at.txt"
  test -s "$geo_r18_live/codex-group-2/completed-at.txt"
fi
test "$(git -C "$geo_r18_site" rev-parse HEAD^{tree})" = ad41cd32f93433b1be065fc8d1969d8da78f2600
for geo_r18_file in README.md index.html llms.txt method.html paper.html research-context.html site-config.js; do
  curl --fail --silent --show-error --max-time 45 --header 'Cache-Control: no-cache' \
    "https://eau-meta-agent.github.io/$geo_r18_file?r18=dda361d-$geo_r18_phase" \
    --output "$geo_r18_live/served-$geo_r18_phase/$geo_r18_file"
  cmp "$geo_r18_live/served-$geo_r18_phase/$geo_r18_file" "$geo_r18_site/$geo_r18_file"
done
git -C "$geo_r18_site" ls-remote origin refs/heads/main > "$geo_r18_live/origin-main-$geo_r18_phase.txt"
test "$(cut -f1 "$geo_r18_live/origin-main-$geo_r18_phase.txt")" = "$(git -C "$geo_r18_site" rev-parse HEAD)"
date -u '+%Y-%m-%dT%H:%M:%SZ' > "$geo_r18_live/verified-$geo_r18_phase.txt"
printf 'R18 all seven served resources %s verification passed\n' "$geo_r18_phase"
