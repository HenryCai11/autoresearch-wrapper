#!/bin/bash
# Step 2 of 2 (Slurm job, no internet needed): install the staged gems, compiling
# native extensions on a compute node rather than a login node.
#   sbatch --account=<acct> --time=00:30:00 --mem=4G --cpus-per-task=4 geo/scripts/setup_jekyll.sh
set -euo pipefail
GEMS="${GEO_GEMS:-${SCRATCH:-$HOME}/geo-gems}"
[ -d "$GEMS/vendor/cache" ] || { echo "run geo/scripts/stage_gems.sh first" >&2; exit 1; }
cd "$GEMS"
export BUNDLE_GEMFILE="$GEMS/Gemfile" BUNDLE_PATH="$GEMS/vendor"
bundle install --local --jobs "${SLURM_CPUS_PER_TASK:-4}"
bundle exec jekyll --version
echo "GEO_GEMS=$GEMS ready"
