#!/bin/bash
set -euo pipefail
test -n "${SLURM_JOB_ID:?Use Slurm}"
export PYTHONPATH=/project/aip-xiye17/henrycai/autoresearch-wrapper
python3 -m py_compile /scratch/henrycai/geo-runs/eau-r19-20261019/candidate_r19.py /scratch/henrycai/geo-runs/eau-r19-20261019/archive_prepared_r19.py
python3 /scratch/henrycai/geo-runs/eau-r19-20261019/candidate_r19.py
python3 /scratch/henrycai/geo-runs/eau-r19-20261019/archive_prepared_r19.py
