#!/bin/bash
set -euo pipefail
test -n "${SLURM_JOB_ID:?Run scoring inside Slurm}"
export PYTHONPATH=/project/aip-xiye17/henrycai/autoresearch-wrapper
python3 -m py_compile /scratch/henrycai/geo-runs/eau-r11-20261016/record_deployment.py /scratch/henrycai/geo-runs/eau-r11-20261016/summarize_outer_live.py /scratch/henrycai/geo-runs/eau-r11-20261016/finalize_r11_measurement.py /scratch/henrycai/geo-runs/eau-r11-20261016/archive_r11_live.py /scratch/henrycai/geo-runs/eau-r11-20261016/audit_r11.py
python3 /scratch/henrycai/geo-runs/eau-r11-20261016/record_deployment.py
python3 /scratch/henrycai/geo-runs/eau-r11-20261016/summarize_outer_live.py
python3 /scratch/henrycai/geo-runs/eau-r11-20261016/finalize_r11_measurement.py
python3 /scratch/henrycai/geo-runs/eau-r11-20261016/archive_r11_live.py
python3 /scratch/henrycai/geo-runs/eau-r11-20261016/audit_r11.py
