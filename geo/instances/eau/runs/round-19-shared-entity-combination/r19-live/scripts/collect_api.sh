#!/bin/bash
# Network-only collector. Headers go to curl stdin and are never saved or echoed.
set -euo pipefail
set +x
test -n "${TAVILY_API_KEY:?Missing inherited Tavily environment}"
test -n "${EXA_API_KEY:?Missing inherited Exa environment}"
geo_r19_root=/scratch/henrycai/geo-runs/eau-r19-20261019
geo_r19_live="$geo_r19_root/r19-live"
test -s "$geo_r19_live/verified-before.txt"
test ! -e "$geo_r19_live/network-events.jsonl"
geo_r19_index=0
while IFS= read -r geo_r19_query; do
  geo_r19_index=$((geo_r19_index + 1))
  geo_r19_number="$(printf '%02d' "$geo_r19_index")"
  for geo_r19_provider in tavily exa; do
    geo_r19_request="$geo_r19_live/$geo_r19_provider-raw/$geo_r19_number-request.json"
    geo_r19_response="$geo_r19_live/$geo_r19_provider-raw/$geo_r19_number.json"
    if [ "$geo_r19_provider" = tavily ]; then
      jq -nc --arg query "$geo_r19_query" '{query:$query,topic:"general",search_depth:"basic",max_results:10,include_answer:false,include_raw_content:false,include_images:false}' > "$geo_r19_request"
      geo_r19_endpoint=https://api.tavily.com/search
    else
      jq -nc --arg query "$geo_r19_query" '{query:$query,type:"auto",numResults:10,contents:{highlights:true}}' > "$geo_r19_request"
      geo_r19_endpoint=https://api.exa.ai/search
    fi
    geo_r19_started="$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
    geo_r19_code=0
    if [ "$geo_r19_provider" = tavily ]; then
      geo_r19_http="$(printf 'header = "Authorization: Bearer %s"\n' "$TAVILY_API_KEY" | curl --config - --silent --show-error --max-time 60 --header 'Content-Type: application/json' --data-binary "@$geo_r19_request" --output "$geo_r19_response" --write-out '%{http_code}' "$geo_r19_endpoint")" || geo_r19_code=$?
    else
      geo_r19_http="$(printf 'header = "x-api-key: %s"\n' "$EXA_API_KEY" | curl --config - --silent --show-error --max-time 60 --header 'Content-Type: application/json' --data-binary "@$geo_r19_request" --output "$geo_r19_response" --write-out '%{http_code}' "$geo_r19_endpoint")" || geo_r19_code=$?
    fi
    geo_r19_ended="$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
    jq -nc --arg query "$geo_r19_query" --arg provider "$geo_r19_provider" --arg http "$geo_r19_http" --arg started_at "$geo_r19_started" --arg ended_at "$geo_r19_ended" --argjson exit_code "$geo_r19_code" '{query:$query,provider:$provider,http:$http,started_at:$started_at,ended_at:$ended_at,exit_code:$exit_code}' >> "$geo_r19_live/network-events.jsonl"
    printf '%s Q%s HTTP %s\n' "$geo_r19_provider" "$geo_r19_number" "$geo_r19_http"
  done
done < "$geo_r19_root/queries.txt"
