#!/bin/bash
# Collect web-search answers from Codex CLI (OpenAI web search, using the local
# ChatGPT login; no API key) for each query, as {"query", "text"} JSONL. Judge them
# afterwards with:  geo_eval probe-judge --engine codex-search --answers <out> ...
#   geo/scripts/probe_codex.sh <queries.txt> <out.jsonl>
set -uo pipefail
QUERIES="${1:?usage: probe_codex.sh <queries.txt> <out.jsonl>}"
OUT="${2:?out.jsonl}"
WORK="$(mktemp -d)"
SEARCH_TIMEOUT="${CODEX_SEARCH_TIMEOUT:-300}"
trap 'rm -rf "$WORK"' EXIT
: > "$OUT"
n=0
while IFS= read -r query; do
  [ -z "$query" ] && continue
  n=$((n + 1))
  prompt="Search the web for: ${query}

Report what you find as a search assistant would: a short numbered list of the most relevant results, each with the people involved and their affiliations, and the URL. Do not run any commands."
  # </dev/null: codex reads stdin, which would otherwise swallow the rest of the query list.
  if (cd "$WORK" && timeout "$SEARCH_TIMEOUT" codex --search exec --skip-git-repo-check -s read-only -o "$WORK/answer.txt" "$prompt" < /dev/null > "$WORK/log.txt" 2>&1); then
    text="$(cat "$WORK/answer.txt")"
  else
    text=""
    echo "codex failed for: $query" >&2
  fi
  jq -nc --arg q "$query" --arg t "$text" '{query: $q, text: $t}' >> "$OUT"
  echo "[$n] $query"
done < "$QUERIES"
