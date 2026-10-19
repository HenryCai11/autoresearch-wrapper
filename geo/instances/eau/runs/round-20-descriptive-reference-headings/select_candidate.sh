#!/bin/bash
set -euo pipefail
test -n "${SLURM_JOB_ID:?Use Slurm}"
export PYTHONPATH=/project/aip-xiye17/henrycai/autoresearch-wrapper
python3 -m py_compile /scratch/henrycai/geo-runs/eau-r20-20261019/common.py /scratch/henrycai/geo-runs/eau-r20-20261019/prepare_r20.py
python3 /scratch/henrycai/geo-runs/eau-r20-20261019/prepare_r20.py
