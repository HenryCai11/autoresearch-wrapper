#!/bin/bash
set -euo pipefail
test -n "${SLURM_JOB_ID:?Use Slurm}"
module load StdEnv/2023 nodejs/20.16.0
geo_r20_group="${1:?1 or 2}"
case "$geo_r20_group" in 1|2) ;; *) exit 2 ;; esac
geo_r20_dir="/scratch/henrycai/geo-runs/eau-r20-20261019/r20-live/codex-group-$geo_r20_group"
test -s /scratch/henrycai/geo-runs/eau-r20-20261019/r20-live/verified-before.txt
test ! -e "$geo_r20_dir/answers.jsonl"
curl --silent --show-error --head --max-time 15 --output /dev/null https://chatgpt.com/
export TMPDIR="${SLURM_TMPDIR:?}"
export CODEX_SEARCH_TIMEOUT=90
export CODEX_SEARCH_REASONING_EFFORT=low
date -u '+%Y-%m-%dT%H:%M:%SZ' > "$geo_r20_dir/started-at.txt"
bash /project/aip-xiye17/henrycai/autoresearch-wrapper/geo/scripts/probe_codex.sh "$geo_r20_dir/queries.txt" "$geo_r20_dir/answers.jsonl"
date -u '+%Y-%m-%dT%H:%M:%SZ' > "$geo_r20_dir/completed-at.txt"
