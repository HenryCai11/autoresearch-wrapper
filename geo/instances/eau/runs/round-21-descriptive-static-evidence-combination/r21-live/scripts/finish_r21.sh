#!/bin/bash
set -euo pipefail
test -n "${SLURM_JOB_ID:?Use Slurm}"
export PYTHONPATH=/project/aip-xiye17/henrycai/autoresearch-wrapper
python3 -m py_compile /scratch/henrycai/geo-runs/eau-r21-20261020/record_deployment.py /scratch/henrycai/geo-runs/eau-r21-20261020/summarize_outer_live.py /scratch/henrycai/geo-runs/eau-r21-20261020/finalize_r21_measurement.py /scratch/henrycai/geo-runs/eau-r21-20261020/archive_r21_live.py /scratch/henrycai/geo-runs/eau-r21-20261020/audit_r21.py
python3 /scratch/henrycai/geo-runs/eau-r21-20261020/record_deployment.py
python3 /scratch/henrycai/geo-runs/eau-r21-20261020/summarize_outer_live.py
python3 /scratch/henrycai/geo-runs/eau-r21-20261020/finalize_r21_measurement.py
python3 /scratch/henrycai/geo-runs/eau-r21-20261020/archive_r21_live.py
python3 /scratch/henrycai/geo-runs/eau-r21-20261020/audit_r21.py
