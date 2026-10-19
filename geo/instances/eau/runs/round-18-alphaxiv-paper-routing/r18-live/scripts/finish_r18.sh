#!/bin/bash
set -euo pipefail
test -n "${SLURM_JOB_ID:?Run scoring inside Slurm}"
export PYTHONPATH=/project/aip-xiye17/henrycai/autoresearch-wrapper
python3 -m py_compile /scratch/henrycai/geo-runs/eau-r18-20261018/record_deployment.py /scratch/henrycai/geo-runs/eau-r18-20261018/summarize_outer_live.py /scratch/henrycai/geo-runs/eau-r18-20261018/finalize_r18_measurement.py /scratch/henrycai/geo-runs/eau-r18-20261018/archive_r18_live.py /scratch/henrycai/geo-runs/eau-r18-20261018/audit_r18.py
python3 /scratch/henrycai/geo-runs/eau-r18-20261018/record_deployment.py
python3 /scratch/henrycai/geo-runs/eau-r18-20261018/summarize_outer_live.py
python3 /scratch/henrycai/geo-runs/eau-r18-20261018/finalize_r18_measurement.py
python3 /scratch/henrycai/geo-runs/eau-r18-20261018/archive_r18_live.py
python3 /scratch/henrycai/geo-runs/eau-r18-20261018/audit_r18.py
