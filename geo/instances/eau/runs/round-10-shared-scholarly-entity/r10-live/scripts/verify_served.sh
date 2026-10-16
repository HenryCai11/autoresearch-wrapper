#!/bin/bash
set -euo pipefail
geo_r10_phase="${1:?before or after}"
case "$geo_r10_phase" in before|after) ;; *) exit 2 ;; esac
geo_r10_live=/scratch/henrycai/geo-runs/eau-r10-20261016/r10-live
geo_r10_site=/project/aip-xiye17/henrycai/eau-meta-agent.github.io
for geo_r10_file in index.html method.html paper.html research-context.html; do
  curl --fail --silent --show-error --max-time 45 --header 'Cache-Control: no-cache' \
    "https://eau-meta-agent.github.io/$geo_r10_file?r10=04e7ea4-$geo_r10_phase" \
    --output "$geo_r10_live/served-$geo_r10_phase/$geo_r10_file"
  cmp "$geo_r10_live/served-$geo_r10_phase/$geo_r10_file" "$geo_r10_site/$geo_r10_file"
done
test "$(git -C "$geo_r10_site" rev-parse HEAD^{tree})" = 14fdd73cd91dc01843dbe6a57b8f172cd249ea98
git -C "$geo_r10_site" ls-remote origin refs/heads/main > "$geo_r10_live/origin-main-$geo_r10_phase.txt"
test "$(cut -f1 "$geo_r10_live/origin-main-$geo_r10_phase.txt")" = b70597085286d4ff4c2d3de78f25d95581835b98
date -u '+%Y-%m-%dT%H:%M:%SZ' > "$geo_r10_live/verified-$geo_r10_phase.txt"
sha256sum "$geo_r10_live/served-$geo_r10_phase/"*.html
echo "R10 four-resource $geo_r10_phase verification passed"
