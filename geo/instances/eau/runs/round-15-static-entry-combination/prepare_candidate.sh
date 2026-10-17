#!/bin/bash
set -euo pipefail
test -n "${SLURM_JOB_ID:?Run inside Slurm}"
export PYTHONPATH=/project/aip-xiye17/henrycai/autoresearch-wrapper
python3 -m py_compile /scratch/henrycai/geo-runs/eau-r15-20261017/common.py /scratch/henrycai/geo-runs/eau-r15-20261017/prepare_r15.py /scratch/henrycai/geo-runs/eau-r15-20261017/candidate_r15.py /scratch/henrycai/geo-runs/eau-r15-20261017/archive_prepared_r15.py
python3 /scratch/henrycai/geo-runs/eau-r15-20261017/candidate_r15.py
python3 /scratch/henrycai/geo-runs/eau-r15-20261017/archive_prepared_r15.py
