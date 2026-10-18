#!/bin/bash
set -euo pipefail
test -n "${SLURM_JOB_ID:?Run inside Slurm}"
export PYTHONPATH=/project/aip-xiye17/henrycai/autoresearch-wrapper
python3 -m py_compile /scratch/henrycai/geo-runs/eau-r18-20261018/common.py /scratch/henrycai/geo-runs/eau-r18-20261018/prepare_r18.py
python3 /scratch/henrycai/geo-runs/eau-r18-20261018/prepare_r18.py
