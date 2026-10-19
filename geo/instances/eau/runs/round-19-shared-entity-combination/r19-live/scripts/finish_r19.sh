#!/bin/bash
set -euo pipefail
test -n "${SLURM_JOB_ID:?Run scoring inside Slurm}"
export PYTHONPATH=/project/aip-xiye17/henrycai/autoresearch-wrapper
python3 -m py_compile /scratch/henrycai/geo-runs/eau-r19-20261019/record_deployment.py /scratch/henrycai/geo-runs/eau-r19-20261019/summarize_outer_live.py /scratch/henrycai/geo-runs/eau-r19-20261019/finalize_r19_measurement.py /scratch/henrycai/geo-runs/eau-r19-20261019/archive_r19_live.py /scratch/henrycai/geo-runs/eau-r19-20261019/audit_r19.py
python3 /scratch/henrycai/geo-runs/eau-r19-20261019/record_deployment.py
python3 /scratch/henrycai/geo-runs/eau-r19-20261019/summarize_outer_live.py
python3 /scratch/henrycai/geo-runs/eau-r19-20261019/finalize_r19_measurement.py
python3 /scratch/henrycai/geo-runs/eau-r19-20261019/archive_r19_live.py
python3 /scratch/henrycai/geo-runs/eau-r19-20261019/audit_r19.py
