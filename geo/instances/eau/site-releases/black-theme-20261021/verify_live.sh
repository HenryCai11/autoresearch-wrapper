#!/bin/bash
set -euo pipefail
eau_dark_root=/scratch/henrycai/geo-runs/eau-black-theme-20261021
eau_dark_source=/scratch/henrycai/eau-black-theme-20261021
eau_dark_at="$(date -u '+%Y%m%dT%H%M%SZ')"
eau_dark_dir="$eau_dark_root/served-$eau_dark_at"
mkdir -p "$eau_dark_dir/assets"
for eau_dark_file in index.html styles.css assets/icons.svg assets/octicons-LICENSE.txt; do
  curl --fail --silent --show-error --max-time 45 --header 'Cache-Control: no-cache' "https://eau-meta-agent.github.io/$eau_dark_file?theme=black-$eau_dark_at" --output "$eau_dark_dir/$eau_dark_file"
  if ! cmp "$eau_dark_source/$eau_dark_file" "$eau_dark_dir/$eau_dark_file"; then
    jq -nc --arg at "$eau_dark_at" --arg file "$eau_dark_file" '{at:$at,file:$file,matched:false}' >> "$eau_dark_root/served-attempts.jsonl"
    exit 1
  fi
done
git -C /project/aip-xiye17/henrycai/eau-meta-agent.github.io ls-remote origin refs/heads/main > "$eau_dark_root/origin-main.txt"
test "$(cut -f1 "$eau_dark_root/origin-main.txt")" = "$(jq -r .production_commit "$eau_dark_root/published.json")"
jq -nc --arg at "$eau_dark_at" --arg dir "$eau_dark_dir" '{at:$at,matched:true,resources:4,served_dir:$dir}' >> "$eau_dark_root/served-attempts.jsonl"
date -u '+%Y-%m-%dT%H:%M:%SZ' > "$eau_dark_root/served-verified-at.txt"
printf 'Black theme and icon resources match production\n'
