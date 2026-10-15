#!/bin/bash
# Build a Jekyll site into <dest> using the gems from setup_jekyll.sh.
# Builds from a temporary copy so caches never land in the source tree (a candidate
# worktree would otherwise commit them).
#   geo/scripts/build_site.sh <site-source-dir> <dest-dir>
set -euo pipefail
SRC="$(cd "${1:?usage: build_site.sh <src> <dest>}" && pwd -P)"
DEST="${2:?usage: build_site.sh <src> <dest>}"
GEMS="${GEO_GEMS:-${SCRATCH:-$HOME}/geo-gems}"
WORK="$(mktemp -d "${SLURM_TMPDIR:-${TMPDIR:-/tmp}}/geo-build.XXXXXX")"
trap 'rm -rf "$WORK"' EXIT
tar -C "$SRC" --exclude=.git --exclude=_site --exclude=.jekyll-cache --exclude=.sass-cache -cf - . | tar -C "$WORK" -xf -
export BUNDLE_GEMFILE="$GEMS/Gemfile" BUNDLE_PATH="$GEMS/vendor"
# Avoid GitHub API lookups from jekyll-github-metadata on offline compute nodes.
export PAGES_REPO_NWO="${PAGES_REPO_NWO:-local/site}" JEKYLL_ENV=production
mkdir -p "$DEST"
bundle exec jekyll build --quiet --source "$WORK" --destination "$(cd "$DEST" && pwd -P)"
