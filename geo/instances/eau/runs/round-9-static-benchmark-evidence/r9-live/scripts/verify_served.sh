#!/bin/bash
set -euo pipefail
geo_r9_phase="${1:?before or after}"
case "$geo_r9_phase" in before|after) ;; *) exit 2 ;; esac
geo_r9_live=/scratch/henrycai/geo-runs/eau-r9-20261016/r9-live
geo_r9_site=/project/aip-xiye17/henrycai/eau-meta-agent.github.io
curl --fail --silent --show-error --max-time 45 --header 'Cache-Control: no-cache' \
  "https://eau-meta-agent.github.io/?r9=9bb531c-$geo_r9_phase" \
  --output "$geo_r9_live/served-$geo_r9_phase/index.html"
cmp "$geo_r9_live/served-$geo_r9_phase/index.html" "$geo_r9_site/index.html"
test "$(git -C "$geo_r9_site" rev-parse HEAD^{tree})" = 5ebd5d1c28e00690d58caafa0edfe066ae5307d7
git -C "$geo_r9_site" ls-remote origin refs/heads/main > "$geo_r9_live/origin-main-$geo_r9_phase.txt"
test "$(cut -f1 "$geo_r9_live/origin-main-$geo_r9_phase.txt")" = 52dee0ba78885b9a3028760ba8d9cfc749a6c2e7
date -u '+%Y-%m-%dT%H:%M:%SZ' > "$geo_r9_live/verified-$geo_r9_phase.txt"
sha256sum "$geo_r9_live/served-$geo_r9_phase/index.html"
echo "R9 homepage $geo_r9_phase verification passed"
