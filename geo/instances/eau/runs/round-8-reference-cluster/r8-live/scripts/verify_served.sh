#!/bin/bash
# Network-only verification. Homepage bytes alone cannot identify R8.
set -euo pipefail
geo_r8_phase="${1:?before or after}"
case "$geo_r8_phase" in before|after) ;; *) exit 2 ;; esac
geo_r8_live=/scratch/henrycai/geo-runs/eau-r8-20261016/r8-live
geo_r8_site=/project/aip-xiye17/henrycai/eau-meta-agent.github.io
for geo_r8_file in method.html research-context.html paper.html llms.txt; do
  curl --fail --silent --show-error --max-time 45 --header 'Cache-Control: no-cache' \
    "https://eau-meta-agent.github.io/$geo_r8_file?r8=a2e3d01-$geo_r8_phase" \
    --output "$geo_r8_live/served-$geo_r8_phase/$geo_r8_file"
  if ! cmp --silent "$geo_r8_live/served-$geo_r8_phase/$geo_r8_file" "$geo_r8_site/$geo_r8_file"; then
    echo "R8 not yet byte-verified: $geo_r8_file" >&2
    exit 3
  fi
done
git -C "$geo_r8_site" ls-remote origin refs/heads/main > "$geo_r8_live/origin-main-$geo_r8_phase.txt"
test "$(cut -f1 "$geo_r8_live/origin-main-$geo_r8_phase.txt")" = 4147abc262bbb69df7a170eb403bf1b6807869f4
date -u '+%Y-%m-%dT%H:%M:%SZ' > "$geo_r8_live/verified-$geo_r8_phase.txt"
sha256sum "$geo_r8_live/served-$geo_r8_phase/method.html" "$geo_r8_live/served-$geo_r8_phase/research-context.html" \
  "$geo_r8_live/served-$geo_r8_phase/paper.html" "$geo_r8_live/served-$geo_r8_phase/llms.txt"
echo "R8 four-resource $geo_r8_phase verification passed"
