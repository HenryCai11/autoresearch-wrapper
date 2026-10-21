#!/bin/bash
set -euo pipefail
geo_phase="${1:?before or after}"
case "$geo_phase" in before|after) ;; *) exit 2 ;; esac
geo_live=/scratch/henrycai/geo-runs/eau-r22-publish-20261021/r22-live
geo_site=/project/aip-xiye17/henrycai/eau-meta-agent.github.io
geo_candidate=/scratch/henrycai/eau-r22-20261021.autoresearch-worktrees/20261021T090905Z-paper-html/candidate-001
test ! -e "$geo_live/verified-$geo_phase.txt"
if [ "$geo_phase" = after ]; then
  for geo_provider in gpt-web tavily exa; do test "$(wc -l < "$geo_live/$geo_provider-answers.jsonl")" = 15; done
  test "$(wc -l < "$geo_live/codex-group-1/answers.jsonl")" = 8
  test "$(wc -l < "$geo_live/codex-group-2/answers.jsonl")" = 7
  test -s "$geo_live/codex-group-1/completed-at.txt"
  test -s "$geo_live/codex-group-2/completed-at.txt"
fi
test "$(git -C "$geo_site" rev-parse HEAD^{tree})" = 1ac57c63402d39d6f7738414ff00bf9837305759
geo_attempt="$(date -u '+%Y%m%dT%H%M%SZ')"
geo_dir="$geo_live/served-$geo_phase-attempt-$geo_attempt"
mkdir "$geo_dir"
for geo_file in README.md index.html llms.txt paper.html site-config.js; do
  curl --fail --silent --show-error --max-time 45 --header 'Cache-Control: no-cache' "https://eau-meta-agent.github.io/$geo_file?r22=fae4460-$geo_phase-$geo_attempt" --output "$geo_dir/$geo_file"
  if ! cmp "$geo_dir/$geo_file" "$geo_candidate/$geo_file"; then
    jq -nc --arg phase "$geo_phase" --arg at "$geo_attempt" --arg file "$geo_file" '{phase:$phase,at:$at,file:$file,matched:false,searches_started:($phase=="after")}' >> "$geo_live/served-verification-attempts.jsonl"
    exit 1
  fi
  cmp "$geo_candidate/$geo_file" "$geo_site/$geo_file"
done
git -C "$geo_site" ls-remote origin refs/heads/main > "$geo_live/origin-main-$geo_phase.txt"
test "$(cut -f1 "$geo_live/origin-main-$geo_phase.txt")" = "$(git -C "$geo_site" rev-parse HEAD)"
for geo_file in README.md index.html llms.txt paper.html site-config.js; do cp "$geo_dir/$geo_file" "$geo_live/served-$geo_phase/$geo_file"; done
date -u '+%Y-%m-%dT%H:%M:%SZ' > "$geo_live/verified-$geo_phase.txt"
jq -nc --arg phase "$geo_phase" --arg at "$geo_attempt" '{phase:$phase,at:$at,matched:true,resources:5}' >> "$geo_live/served-verification-attempts.jsonl"
printf 'R22 all five changed served resources %s verification passed\n' "$geo_phase"
