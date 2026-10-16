#!/bin/bash
# Step 1 of 2 (login node, needs internet): resolve and download a site's gems into
# $GEO_GEMS/vendor/cache without installing or compiling anything. Compute nodes on
# some clusters cannot reach rubygems.org, so the install (step 2) runs offline.
#   geo/scripts/stage_gems.sh <site-repo>
set -euo pipefail
SITE="${1:?usage: stage_gems.sh <site-repo>}"
GEMS="${GEO_GEMS:-${SCRATCH:-$HOME}/geo-gems}"
mkdir -p "$GEMS"
# Live-reload/dev-only gems are not needed to build, and hawkins needs a C build.
grep -v -E "hawkins|wdm" "$SITE/Gemfile" > "$GEMS/Gemfile"
cd "$GEMS"
BUNDLE_GEMFILE="$GEMS/Gemfile" BUNDLE_PATH="$GEMS/vendor" bundle cache --no-install
echo "staged $(ls "$GEMS/vendor/cache" | wc -l) gems in $GEMS/vendor/cache"
