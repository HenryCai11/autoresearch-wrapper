#!/bin/bash
set -euo pipefail
test -n "${SLURM_JOB_ID:?Use Slurm}"
export PYTHONPATH=/project/aip-xiye17/henrycai/autoresearch-wrapper
stage="${1:?Specify prepare, allocate, validate, or archive}"
case "$stage" in
  prepare) script=prepare_r22.py ;;
  allocate) script=allocate_r22.py ;;
  validate) script=validate_r22.py ;;
  archive) script=archive_r22.py ;;
  *) exit 2 ;;
esac
python3 -m py_compile "/scratch/henrycai/geo-runs/eau-r22-20261021/$script"
python3 "/scratch/henrycai/geo-runs/eau-r22-20261021/$script"
