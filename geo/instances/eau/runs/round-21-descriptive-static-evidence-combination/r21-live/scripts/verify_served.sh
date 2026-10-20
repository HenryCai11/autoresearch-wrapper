#!/bin/bash
set -euo pipefail
geo_r21_phase="${1:?before or after}"
case "$geo_r21_phase" in before|after) ;; *) exit 2 ;; esac
geo_r21_live=/scratch/henrycai/geo-runs/eau-r21-20261020/r21-live
geo_r21_site=/project/aip-xiye17/henrycai/eau-meta-agent.github.io
geo_r21_candidate=/scratch/henrycai/eau-r21-20261020.autoresearch-worktrees/20261020T055744Z-index-html/candidate-001
test ! -e "$geo_r21_live/verified-$geo_r21_phase.txt"
if [ "$geo_r21_phase" = after ]; then
  test "$(wc -l < "$geo_r21_live/gpt-web-answers.jsonl")" = 15
  test "$(wc -l < "$geo_r21_live/tavily-answers.jsonl")" = 15
  test "$(wc -l < "$geo_r21_live/exa-answers.jsonl")" = 15
  test "$(wc -l < "$geo_r21_live/codex-group-1/answers.jsonl")" = 8
  test "$(wc -l < "$geo_r21_live/codex-group-2/answers.jsonl")" = 7
  test -s "$geo_r21_live/codex-group-1/completed-at.txt"
  test -s "$geo_r21_live/codex-group-2/completed-at.txt"
fi
test "$(git -C "$geo_r21_site" rev-parse HEAD^{tree})" = 49c3d78bb28cbadbcfa7dc78673b8a104f640084
geo_r21_attempt="$(date -u '+%Y%m%dT%H%M%SZ')"
geo_r21_dir="$geo_r21_live/served-$geo_r21_phase-attempt-$geo_r21_attempt"
mkdir "$geo_r21_dir"
for geo_r21_file in index.html method.html research-context.html; do
  curl --fail --silent --show-error --max-time 45 --header 'Cache-Control: no-cache' \
    "https://eau-meta-agent.github.io/$geo_r21_file?r21=a2db6f6-$geo_r21_phase-$geo_r21_attempt" --output "$geo_r21_dir/$geo_r21_file"
  if ! cmp "$geo_r21_dir/$geo_r21_file" "$geo_r21_candidate/$geo_r21_file"; then
    jq -nc --arg phase "$geo_r21_phase" --arg at "$geo_r21_attempt" --arg file "$geo_r21_file" '{phase:$phase,at:$at,file:$file,matched:false,searches_started:($phase=="after")}' >> "$geo_r21_live/served-verification-attempts.jsonl"
    exit 1
  fi
  cmp "$geo_r21_candidate/$geo_r21_file" "$geo_r21_site/$geo_r21_file"
done
git -C "$geo_r21_site" ls-remote origin refs/heads/main > "$geo_r21_live/origin-main-$geo_r21_phase.txt"
test "$(cut -f1 "$geo_r21_live/origin-main-$geo_r21_phase.txt")" = "$(git -C "$geo_r21_site" rev-parse HEAD)"
cp "$geo_r21_dir/"*.html "$geo_r21_live/served-$geo_r21_phase/"
date -u '+%Y-%m-%dT%H:%M:%SZ' > "$geo_r21_live/verified-$geo_r21_phase.txt"
jq -nc --arg phase "$geo_r21_phase" --arg at "$geo_r21_attempt" '{phase:$phase,at:$at,matched:true,resources:3}' >> "$geo_r21_live/served-verification-attempts.jsonl"
printf 'R21 all three changed served resources %s verification passed\n' "$geo_r21_phase"
