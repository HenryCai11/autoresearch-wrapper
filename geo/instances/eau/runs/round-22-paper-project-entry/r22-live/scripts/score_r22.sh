#!/bin/bash
set -euo pipefail
test -n "${SLURM_JOB_ID:?Use Slurm}"
export PYTHONPATH=/project/aip-xiye17/henrycai/autoresearch-wrapper
python3 /scratch/henrycai/geo-runs/eau-r22-publish-20261021/record_deployment.py
python3 /scratch/henrycai/geo-runs/eau-r22-publish-20261021/summarize_outer_live.py
python3 /scratch/henrycai/geo-runs/eau-r22-publish-20261021/finalize_r22_measurement.py
