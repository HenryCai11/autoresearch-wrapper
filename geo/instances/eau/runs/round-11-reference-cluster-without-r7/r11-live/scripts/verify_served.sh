#!/bin/bash
set -euo pipefail
geo_r11_phase="${1:?before or after}"
case "$geo_r11_phase" in before|after) ;; *) exit 2 ;; esac
geo_r11_live=/scratch/henrycai/geo-runs/eau-r11-20261016/r11-live
geo_r11_site=/project/aip-xiye17/henrycai/eau-meta-agent.github.io
for geo_r11_file in index.html method.html paper.html research-context.html; do
  curl --fail --silent --show-error --max-time 45 --header 'Cache-Control: no-cache' \
    "https://eau-meta-agent.github.io/$geo_r11_file?r11=8e9ed30-$geo_r11_phase" \
    --output "$geo_r11_live/served-$geo_r11_phase/$geo_r11_file"
  cmp "$geo_r11_live/served-$geo_r11_phase/$geo_r11_file" "$geo_r11_site/$geo_r11_file"
done
test "$(git -C "$geo_r11_site" rev-parse HEAD^{tree})" = ccf91bf07379aae81ec4ba3c698803d0bd69368c
git -C "$geo_r11_site" ls-remote origin refs/heads/main > "$geo_r11_live/origin-main-$geo_r11_phase.txt"
test "$(cut -f1 "$geo_r11_live/origin-main-$geo_r11_phase.txt")" = c744ba125108d003ea61e8b89807e274ffaa6e4e
date -u '+%Y-%m-%dT%H:%M:%SZ' > "$geo_r11_live/verified-$geo_r11_phase.txt"
sha256sum "$geo_r11_live/served-$geo_r11_phase/"*.html
echo "R11 four-resource $geo_r11_phase verification passed"
