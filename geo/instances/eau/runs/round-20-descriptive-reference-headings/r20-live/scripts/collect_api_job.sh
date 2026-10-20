#!/bin/bash
set -euo pipefail
test -n "${SLURM_JOB_ID:?Use Slurm}"
set +x
export PYTHONPATH=/project/aip-xiye17/henrycai/autoresearch-wrapper
bash /scratch/henrycai/geo-runs/eau-r20-20261019/collect_api.sh
python3 /scratch/henrycai/geo-runs/eau-r20-20261019/normalize_api.py
