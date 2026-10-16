#!/bin/bash
set -euo pipefail
geo_r12_phase="${1:?before or after}"
case "$geo_r12_phase" in before|after) ;; *) exit 2 ;; esac
geo_r12_live=/scratch/henrycai/geo-runs/eau-r12-20261016/r12-live
geo_r12_site=/project/aip-xiye17/henrycai/eau-meta-agent.github.io
curl --fail --silent --show-error --max-time 45 --header 'Cache-Control: no-cache' \
  "https://eau-meta-agent.github.io/index.html?r12=95940d5-$geo_r12_phase" \
  --output "$geo_r12_live/served-$geo_r12_phase/index.html"
cmp "$geo_r12_live/served-$geo_r12_phase/index.html" "$geo_r12_site/index.html"
test "$(git -C "$geo_r12_site" rev-parse HEAD^{tree})" = c2e643d4d1462b72bc4914de9222cfb200be07e3
git -C "$geo_r12_site" ls-remote origin refs/heads/main > "$geo_r12_live/origin-main-$geo_r12_phase.txt"
test "$(cut -f1 "$geo_r12_live/origin-main-$geo_r12_phase.txt")" = bbc3b79d20323549fd29e422017ed6c457c6b707
date -u '+%Y-%m-%dT%H:%M:%SZ' > "$geo_r12_live/verified-$geo_r12_phase.txt"
sha256sum "$geo_r12_live/served-$geo_r12_phase/index.html"
echo "R12 homepage $geo_r12_phase verification passed"
