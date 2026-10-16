#!/bin/bash
set -euo pipefail
test -n "${SLURM_JOB_ID:?Run inside Slurm}"
export PYTHONPATH=/project/aip-xiye17/henrycai/autoresearch-wrapper
python3 /scratch/henrycai/geo-runs/eau-r10-20261016/prepare_r10.py
python3 /scratch/henrycai/geo-runs/eau-r10-20261016/allocate_r10.py
