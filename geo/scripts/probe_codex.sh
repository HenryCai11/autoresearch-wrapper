#!/bin/bash
# Collect web-search answers from Codex CLI (OpenAI web search, using the local
# ChatGPT login; no API key) for each query, as {"query", "text"} JSONL. Judge them
# afterwards with:  geo_eval probe-judge --engine codex-search --answers <out> ...
#   geo/scripts/probe_codex.sh <queries.txt> <out.jsonl>
set -uo pipefail
QUERIES="${1:?usage: probe_codex.sh <queries.txt> <out.jsonl>}"
OUT="${2:?out.jsonl}"
WORK="$(mktemp -d)"
SEARCH_TIMEOUT="${CODEX_SEARCH_TIMEOUT:-90}"
REASONING_EFFORT="${CODEX_SEARCH_REASONING_EFFORT:-low}"
LOG_DIR="${OUT%.jsonl}.logs"
mkdir -p "$LOG_DIR"
trap 'rm -rf "$WORK"' EXIT
: > "$OUT"
n=0
while IFS= read -r query; do
  [ -z "$query" ] && continue
  n=$((n + 1))
  prompt="Search the web for: ${query}

Report what you find as a search assistant would: a short numbered list of the most relevant results, each with the people involved and their affiliations, and the URL. Do not run any commands."
  # </dev/null: codex reads stdin, which would otherwise swallow the rest of the query list.
  started="$(date +%s)"
  if (cd "$WORK" && timeout "$SEARCH_TIMEOUT" codex --search exec --skip-git-repo-check \
      -c "model_reasoning_effort=${REASONING_EFFORT}" -s read-only \
      -o "$WORK/answer.txt" "$prompt" < /dev/null > "$WORK/log.txt" 2>&1); then
    exit_code=0
    text="$(cat "$WORK/answer.txt")"
    status="ok"
  else
    exit_code=$?
    text=""
    if [ "$exit_code" -eq 124 ]; then status="timeout"; else status="error"; fi
    echo "codex ${status} (exit ${exit_code}) for: $query" >&2
  fi
  elapsed="$(( $(date +%s) - started ))"
  cp "$WORK/log.txt" "$LOG_DIR/query-$(printf '%02d' "$n").log"
  jq -nc --arg q "$query" --arg t "$text" --arg status "$status" \
    --argjson exit_code "$exit_code" --argjson elapsed_seconds "$elapsed" \
    '{query: $q, text: $t, status: $status, exit_code: $exit_code, elapsed_seconds: $elapsed_seconds}' >> "$OUT"
  echo "[$n] $query"
done < "$QUERIES"
