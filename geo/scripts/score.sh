#!/bin/bash
# Metric command for a GEO instance: build the site in the current directory and
# score it with geo_eval. Prints the eval matrix and a final METRIC=<0-100> line.
#   geo/scripts/score.sh <instance-dir> [extra geo_eval matrix args]
# On a cluster, run it through Slurm, e.g.:
#   srun --account=<acct> --time=00:20:00 --mem=4G --cpus-per-task=2 geo/scripts/score.sh <instance-dir>
set -euo pipefail
INSTANCE="$(cd "${1:?usage: score.sh <instance-dir> [args]}" && pwd -P)"
shift
HERE="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd -P)"
ROOT="$(dirname "$(dirname "$HERE")")"
# shellcheck disable=SC1091
[ -f "$INSTANCE/instance.env" ] && set -a && source "$INSTANCE/instance.env" && set +a
OUT="$(mktemp -d "${SLURM_TMPDIR:-${TMPDIR:-/tmp}}/geo-site.XXXXXX")"
trap 'rm -rf "$OUT"' EXIT
case "${GEO_BUILDER:-jekyll}" in
  jekyll) "$HERE/build_site.sh" . "$OUT" ;;
  static) cp -r "${GEO_STATIC_DIR:-.}/." "$OUT" ;;
  *) echo "unknown GEO_BUILDER: $GEO_BUILDER" >&2; exit 2 ;;
esac
# Keep every evaluation's full report (matrix, checks, answers) when asked, e.g. for
# frontier plots: <GEO_REPORT_DIR>/<worktree-name>-<utc-time>.json
REPORT_ARGS=()
if [ -n "${GEO_REPORT_DIR:-}" ]; then
  mkdir -p "$GEO_REPORT_DIR"
  REPORT_ARGS=(--report "$GEO_REPORT_DIR/$(basename "$PWD")-$(date -u +%Y%m%dT%H%M%SZ).json")
fi
# shellcheck disable=SC2086
exec python3 "$ROOT/scripts/geo_eval.py" matrix --map "$INSTANCE/map.json" --site "$OUT" ${GEO_EVAL_ARGS:-} "${REPORT_ARGS[@]}" "$@"
