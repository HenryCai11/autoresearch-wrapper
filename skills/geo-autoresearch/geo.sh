#!/usr/bin/env bash
set -euo pipefail

# GEO launcher: finds the geo_eval toolkit and geo scripts next to the
# autoresearch-wrapper CLI (repo checkout or plugin package), resolving symlinks.
SELF_PATH="$(readlink -f -- "${BASH_SOURCE[0]}" 2>/dev/null || echo "${BASH_SOURCE[0]}")"
SEARCH_DIR="$(cd -P -- "$(dirname -- "$SELF_PATH")" && pwd -P)"
ROOT=""
while [ "$SEARCH_DIR" != "/" ]; do
  if [ -f "$SEARCH_DIR/scripts/geo_eval.py" ]; then ROOT="$SEARCH_DIR"; break; fi
  SEARCH_DIR="$(dirname "$SEARCH_DIR")"
done
[ -n "$ROOT" ] || { echo "Could not locate scripts/geo_eval.py from $SELF_PATH" >&2; exit 1; }

cmd="${1:-help}"
[ $# -gt 0 ] && shift
case "$cmd" in
  eval)         exec python3 "$ROOT/scripts/geo_eval.py" "$@" ;;      # geo_eval toolkit
  score)        exec "$ROOT/geo/scripts/score.sh" "$@" ;;             # build cwd + eval matrix (metric command)
  build)        exec "$ROOT/geo/scripts/build_site.sh" "$@" ;;
  stage-gems)   exec "$ROOT/geo/scripts/stage_gems.sh" "$@" ;;        # login node: download only
  setup-jekyll) exec "$ROOT/geo/scripts/setup_jekyll.sh" "$@" ;;      # Slurm job: offline install
  fetch-goatcounter) exec "$ROOT/geo/scripts/fetch_goatcounter.sh" "$@" ;;  # curl only; then `eval ood --input-dir`
  root)         echo "$ROOT" ;;
  *) echo "usage: geo.sh {eval|score|build|stage-gems|setup-jekyll|fetch-goatcounter|root} [args]" >&2; exit 2 ;;
esac
