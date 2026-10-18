#!/bin/bash
set -euo pipefail
test -n "${SLURM_JOB_ID:?Run scoring inside Slurm}"
export PYTHONPATH=/project/aip-xiye17/henrycai/autoresearch-wrapper
python3 -m py_compile /scratch/henrycai/geo-runs/eau-r16-20261017/record_deployment.py /scratch/henrycai/geo-runs/eau-r16-20261017/summarize_outer_live.py /scratch/henrycai/geo-runs/eau-r16-20261017/finalize_r16_measurement.py /scratch/henrycai/geo-runs/eau-r16-20261017/archive_r16_live.py /scratch/henrycai/geo-runs/eau-r16-20261017/audit_r16.py
python3 /scratch/henrycai/geo-runs/eau-r16-20261017/record_deployment.py
python3 /scratch/henrycai/geo-runs/eau-r16-20261017/summarize_outer_live.py
python3 /scratch/henrycai/geo-runs/eau-r16-20261017/finalize_r16_measurement.py
python3 /scratch/henrycai/geo-runs/eau-r16-20261017/archive_r16_live.py
python3 /scratch/henrycai/geo-runs/eau-r16-20261017/audit_r16.py
