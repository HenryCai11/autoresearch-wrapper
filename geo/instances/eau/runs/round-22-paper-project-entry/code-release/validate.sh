#!/bin/bash
set -euo pipefail
test -n "${SLURM_JOB_ID:?Use Slurm}"
export PYTHONPATH=/project/aip-xiye17/henrycai/autoresearch-wrapper
python3 -m py_compile /scratch/henrycai/geo-runs/eau-r22-code-release-20261021/update_r22.py
python3 /scratch/henrycai/geo-runs/eau-r22-code-release-20261021/update_r22.py
