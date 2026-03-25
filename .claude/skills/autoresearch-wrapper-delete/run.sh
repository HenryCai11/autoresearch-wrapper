#!/usr/bin/env bash
set -euo pipefail

SELF_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
SEARCH_DIR="$SELF_DIR"

while [ "$SEARCH_DIR" != "/" ]; do
  if [ -f "$SEARCH_DIR/scripts/autoresearch_wrapper.py" ]; then
    exec python3 "$SEARCH_DIR/scripts/autoresearch_wrapper.py" "$@"
  fi
  SEARCH_DIR="$(dirname "$SEARCH_DIR")"
done

echo "Could not locate scripts/autoresearch_wrapper.py from $SELF_DIR" >&2
exit 1
