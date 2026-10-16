#!/bin/bash
set -euo pipefail
test -n "${SLURM_JOB_ID:?Run inside Slurm}"
export PYTHONPATH=/project/aip-xiye17/henrycai/autoresearch-wrapper
python3 -m py_compile /scratch/henrycai/geo-runs/eau-r13-20261016/common.py /scratch/henrycai/geo-runs/eau-r13-20261016/prepare_r13.py /scratch/henrycai/geo-runs/eau-r13-20261016/candidate_r13.py /scratch/henrycai/geo-runs/eau-r13-20261016/archive_prepared_r13.py
python3 /scratch/henrycai/geo-runs/eau-r13-20261016/candidate_r13.py
python3 /scratch/henrycai/geo-runs/eau-r13-20261016/archive_prepared_r13.py
