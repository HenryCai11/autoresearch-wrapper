#!/bin/bash
set -euo pipefail
geo_r20_phase="${1:?before or after}"
case "$geo_r20_phase" in before|after) ;; *) exit 2 ;; esac
geo_r20_live=/scratch/henrycai/geo-runs/eau-r20-20261019/r20-live
geo_r20_site=/project/aip-xiye17/henrycai/eau-meta-agent.github.io
geo_r20_candidate=/scratch/henrycai/eau-r20-20261019.autoresearch-worktrees/20261019T171243Z-method-html/candidate-001
test ! -e "$geo_r20_live/verified-$geo_r20_phase.txt"
if [ "$geo_r20_phase" = after ]; then
  test "$(wc -l < "$geo_r20_live/gpt-web-answers.jsonl")" = 15
  test "$(wc -l < "$geo_r20_live/tavily-answers.jsonl")" = 15
  test "$(wc -l < "$geo_r20_live/exa-answers.jsonl")" = 15
  test "$(wc -l < "$geo_r20_live/codex-group-1/answers.jsonl")" = 8
  test "$(wc -l < "$geo_r20_live/codex-group-2/answers.jsonl")" = 7
  test -s "$geo_r20_live/codex-group-1/completed-at.txt"
  test -s "$geo_r20_live/codex-group-2/completed-at.txt"
fi
test "$(git -C "$geo_r20_site" rev-parse HEAD^{tree})" = 8261df22ebbcfa2edc6031f32e2fb51214822ad3
geo_r20_attempt="$(date -u '+%Y%m%dT%H%M%SZ')"
geo_r20_attempt_dir="$geo_r20_live/served-$geo_r20_phase-attempt-$geo_r20_attempt"
mkdir "$geo_r20_attempt_dir"
for geo_r20_file in index.html method.html paper.html research-context.html; do
  curl --fail --silent --show-error --max-time 45 --header 'Cache-Control: no-cache' \
    "https://eau-meta-agent.github.io/$geo_r20_file?r20=65e2486-$geo_r20_phase-$geo_r20_attempt" \
    --output "$geo_r20_attempt_dir/$geo_r20_file"
  if ! cmp "$geo_r20_attempt_dir/$geo_r20_file" "$geo_r20_candidate/$geo_r20_file"; then
    jq -nc --arg phase "$geo_r20_phase" --arg at "$geo_r20_attempt" --arg file "$geo_r20_file" '{phase:$phase,at:$at,file:$file,matched:false,searches_started:($phase=="after")}' >> "$geo_r20_live/served-verification-attempts.jsonl"
    exit 1
  fi
  cmp "$geo_r20_candidate/$geo_r20_file" "$geo_r20_site/$geo_r20_file"
done
git -C "$geo_r20_site" ls-remote origin refs/heads/main > "$geo_r20_live/origin-main-$geo_r20_phase.txt"
test "$(cut -f1 "$geo_r20_live/origin-main-$geo_r20_phase.txt")" = "$(git -C "$geo_r20_site" rev-parse HEAD)"
cp "$geo_r20_attempt_dir/"*.html "$geo_r20_live/served-$geo_r20_phase/"
date -u '+%Y-%m-%dT%H:%M:%SZ' > "$geo_r20_live/verified-$geo_r20_phase.txt"
jq -nc --arg phase "$geo_r20_phase" --arg at "$geo_r20_attempt" '{phase:$phase,at:$at,matched:true,resources:4}' >> "$geo_r20_live/served-verification-attempts.jsonl"
printf 'R20 all four served resources %s verification passed\n' "$geo_r20_phase"
