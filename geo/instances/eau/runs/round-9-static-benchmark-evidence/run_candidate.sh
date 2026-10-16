#!/bin/bash
set -euo pipefail
# Discovered with module spider nodejs and module spider nodejs/20.16.0.
module load StdEnv/2023 nodejs/20.16.0
export PYTHONPATH=/project/aip-xiye17/henrycai/autoresearch-wrapper
export PYTHONDONTWRITEBYTECODE=1
node --version
python3 /scratch/henrycai/geo-runs/eau-r9-20261016/candidate_r9.py
