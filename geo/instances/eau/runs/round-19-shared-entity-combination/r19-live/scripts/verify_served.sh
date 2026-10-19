#!/bin/bash
set -euo pipefail
geo_r19_phase="${1:?before or after}"
case "$geo_r19_phase" in before|after) ;; *) exit 2 ;; esac
geo_r19_live=/scratch/henrycai/geo-runs/eau-r19-20261019/r19-live
geo_r19_site=/project/aip-xiye17/henrycai/eau-meta-agent.github.io
if [ "$geo_r19_phase" = after ]; then
  test "$(wc -l < "$geo_r19_live/gpt-web-answers.jsonl")" = 15
  test "$(wc -l < "$geo_r19_live/tavily-answers.jsonl")" = 15
  test "$(wc -l < "$geo_r19_live/exa-answers.jsonl")" = 15
  test "$(wc -l < "$geo_r19_live/codex-group-1/answers.jsonl")" = 8
  test "$(wc -l < "$geo_r19_live/codex-group-2/answers.jsonl")" = 7
  test -s "$geo_r19_live/codex-group-1/completed-at.txt"
  test -s "$geo_r19_live/codex-group-2/completed-at.txt"
fi
test "$(git -C "$geo_r19_site" rev-parse HEAD^{tree})" = 12b28c84303366ae8e4117709ec0166c1919ae9a
for geo_r19_file in index.html method.html paper.html research-context.html; do
  curl --fail --silent --show-error --max-time 45 --header 'Cache-Control: no-cache' \
    "https://eau-meta-agent.github.io/$geo_r19_file?r19=6ef90e8-$geo_r19_phase" \
    --output "$geo_r19_live/served-$geo_r19_phase/$geo_r19_file"
  cmp "$geo_r19_live/served-$geo_r19_phase/$geo_r19_file" "$geo_r19_site/$geo_r19_file"
done
git -C "$geo_r19_site" ls-remote origin refs/heads/main > "$geo_r19_live/origin-main-$geo_r19_phase.txt"
test "$(cut -f1 "$geo_r19_live/origin-main-$geo_r19_phase.txt")" = "$(git -C "$geo_r19_site" rev-parse HEAD)"
date -u '+%Y-%m-%dT%H:%M:%SZ' > "$geo_r19_live/verified-$geo_r19_phase.txt"
printf 'R19 all four served resources %s verification passed\n' "$geo_r19_phase"
