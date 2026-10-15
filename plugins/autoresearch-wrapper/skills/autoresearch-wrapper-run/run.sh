#!/usr/bin/env bash
set -euo pipefail

# Resolve symlinks (e.g. ~/.agents/skills/<name> -> <repo>/skills/<name>) so the
# upward search starts inside the repo or plugin, not inside the skills folder.
SELF_PATH="$(readlink -f -- "${BASH_SOURCE[0]}" 2>/dev/null || echo "${BASH_SOURCE[0]}")"
SELF_DIR="$(cd -P -- "$(dirname -- "$SELF_PATH")" && pwd -P)"
SEARCH_DIR="$SELF_DIR"

while [ "$SEARCH_DIR" != "/" ]; do
  if [ -f "$SEARCH_DIR/scripts/autoresearch_wrapper.py" ]; then
    exec python3 "$SEARCH_DIR/scripts/autoresearch_wrapper.py" "$@"
  fi
  SEARCH_DIR="$(dirname "$SEARCH_DIR")"
done

echo "Could not locate scripts/autoresearch_wrapper.py from $SELF_DIR" >&2
exit 1
