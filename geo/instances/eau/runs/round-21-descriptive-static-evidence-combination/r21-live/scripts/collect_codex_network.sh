#!/bin/bash
set -euo pipefail
geo_r21_group="${1:?1 or 2}"
case "$geo_r21_group" in 1|2) ;; *) exit 2 ;; esac
geo_r21_dir="/scratch/henrycai/geo-runs/eau-r21-20261020/r21-live/codex-group-$geo_r21_group"
test -s /scratch/henrycai/geo-runs/eau-r21-20261020/r21-live/verified-before.txt
test ! -e "$geo_r21_dir/answers.jsonl"
export TMPDIR=/scratch/henrycai/geo-runs/eau-r21-20261020/codex-network-temp
mkdir -p "$TMPDIR"
export CODEX_SEARCH_TIMEOUT=90
export CODEX_SEARCH_REASONING_EFFORT=low
date -u '+%Y-%m-%dT%H:%M:%SZ' > "$geo_r21_dir/started-at.txt"
bash /scratch/henrycai/geo-runs/eau-r21-20261020/probe_codex_native.sh "$geo_r21_dir/queries.txt" "$geo_r21_dir/answers.jsonl"
date -u '+%Y-%m-%dT%H:%M:%SZ' > "$geo_r21_dir/completed-at.txt"
