#!/bin/bash
set -euo pipefail
export PYTHONPATH=/project/aip-xiye17/henrycai/autoresearch-wrapper
python3 /scratch/henrycai/geo-runs/eau-r8-20261016/record_deployment.py
python3 /scratch/henrycai/geo-runs/eau-r8-20261016/summarize_outer_live.py
python3 /scratch/henrycai/geo-runs/eau-r8-20261016/finalize_r8_measurement.py
python3 /scratch/henrycai/geo-runs/eau-r8-20261016/archive_r8_live.py
