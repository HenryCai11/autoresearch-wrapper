#!/bin/bash
set -euo pipefail
test -n "${SLURM_JOB_ID:?Run inside Slurm}"
export PYTHONPATH=/project/aip-xiye17/henrycai/autoresearch-wrapper
python3 /scratch/henrycai/geo-runs/eau-r11-20261016/prepare_r11.py
python3 /scratch/henrycai/geo-runs/eau-r11-20261016/candidate_r11.py
python3 /scratch/henrycai/geo-runs/eau-r11-20261016/archive_prepared_r11.py
