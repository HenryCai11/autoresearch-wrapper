#!/bin/bash
set -euo pipefail
test -n "${SLURM_JOB_ID:?Use Slurm}"
export PYTHONPATH=/project/aip-xiye17/henrycai/autoresearch-wrapper
python3 /scratch/henrycai/geo-runs/eau-r22-publish-20261021/archive_r22.py
