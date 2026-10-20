#!/bin/bash
set -euo pipefail
test -n "${SLURM_JOB_ID:?Use Slurm}"
export PYTHONPATH=/project/aip-xiye17/henrycai/autoresearch-wrapper
python3 -m py_compile /scratch/henrycai/geo-runs/eau-r20-20261019/record_deployment.py /scratch/henrycai/geo-runs/eau-r20-20261019/summarize_outer_live.py /scratch/henrycai/geo-runs/eau-r20-20261019/finalize_r20_measurement.py /scratch/henrycai/geo-runs/eau-r20-20261019/archive_r20_live.py /scratch/henrycai/geo-runs/eau-r20-20261019/audit_r20.py
python3 /scratch/henrycai/geo-runs/eau-r20-20261019/record_deployment.py
python3 /scratch/henrycai/geo-runs/eau-r20-20261019/summarize_outer_live.py
python3 /scratch/henrycai/geo-runs/eau-r20-20261019/finalize_r20_measurement.py
python3 /scratch/henrycai/geo-runs/eau-r20-20261019/archive_r20_live.py
python3 /scratch/henrycai/geo-runs/eau-r20-20261019/audit_r20.py
