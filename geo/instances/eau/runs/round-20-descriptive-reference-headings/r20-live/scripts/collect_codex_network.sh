#!/bin/bash
set -euo pipefail
geo_r20_group="${1:?1 or 2}"
case "$geo_r20_group" in 1|2) ;; *) exit 2 ;; esac
geo_r20_dir="/scratch/henrycai/geo-runs/eau-r20-20261019/r20-live/codex-group-$geo_r20_group"
test -s /scratch/henrycai/geo-runs/eau-r20-20261019/r20-live/verified-before.txt
test ! -e "$geo_r20_dir/answers.jsonl"
export TMPDIR=/scratch/henrycai/geo-runs/eau-r20-20261019/codex-network-temp
mkdir -p "$TMPDIR"
export CODEX_SEARCH_TIMEOUT=90
export CODEX_SEARCH_REASONING_EFFORT=low
date -u '+%Y-%m-%dT%H:%M:%SZ' > "$geo_r20_dir/started-at.txt"
bash /scratch/henrycai/geo-runs/eau-r20-20261019/probe_codex_native.sh "$geo_r20_dir/queries.txt" "$geo_r20_dir/answers.jsonl"
date -u '+%Y-%m-%dT%H:%M:%SZ' > "$geo_r20_dir/completed-at.txt"
