#!/bin/bash
# Network-only collector. Headers go to curl stdin and are never saved or echoed.
set -euo pipefail
set +x
test -n "${TAVILY_API_KEY:?Missing inherited Tavily environment}"
test -n "${EXA_API_KEY:?Missing inherited Exa environment}"
geo_r20_root=/scratch/henrycai/geo-runs/eau-r20-20261019
geo_r20_live="$geo_r20_root/r20-live"
test -s "$geo_r20_live/verified-before.txt"
test ! -e "$geo_r20_live/network-events.jsonl"
geo_r20_index=0
while IFS= read -r geo_r20_query; do
  geo_r20_index=$((geo_r20_index + 1))
  geo_r20_number="$(printf '%02d' "$geo_r20_index")"
  for geo_r20_provider in tavily exa; do
    geo_r20_request="$geo_r20_live/$geo_r20_provider-raw/$geo_r20_number-request.json"
    geo_r20_response="$geo_r20_live/$geo_r20_provider-raw/$geo_r20_number.json"
    if [ "$geo_r20_provider" = tavily ]; then
      jq -nc --arg query "$geo_r20_query" '{query:$query,topic:"general",search_depth:"basic",max_results:10,include_answer:false,include_raw_content:false,include_images:false}' > "$geo_r20_request"
      geo_r20_endpoint=https://api.tavily.com/search
    else
      jq -nc --arg query "$geo_r20_query" '{query:$query,type:"auto",numResults:10,contents:{highlights:true}}' > "$geo_r20_request"
      geo_r20_endpoint=https://api.exa.ai/search
    fi
    geo_r20_started="$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
    geo_r20_code=0
    if [ "$geo_r20_provider" = tavily ]; then
      geo_r20_http="$(printf 'header = "Authorization: Bearer %s"\n' "$TAVILY_API_KEY" | curl --config - --silent --show-error --max-time 60 --header 'Content-Type: application/json' --data-binary "@$geo_r20_request" --output "$geo_r20_response" --write-out '%{http_code}' "$geo_r20_endpoint")" || geo_r20_code=$?
    else
      geo_r20_http="$(printf 'header = "x-api-key: %s"\n' "$EXA_API_KEY" | curl --config - --silent --show-error --max-time 60 --header 'Content-Type: application/json' --data-binary "@$geo_r20_request" --output "$geo_r20_response" --write-out '%{http_code}' "$geo_r20_endpoint")" || geo_r20_code=$?
    fi
    geo_r20_ended="$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
    jq -nc --arg query "$geo_r20_query" --arg provider "$geo_r20_provider" --arg http "$geo_r20_http" --arg started_at "$geo_r20_started" --arg ended_at "$geo_r20_ended" --argjson exit_code "$geo_r20_code" '{query:$query,provider:$provider,http:$http,started_at:$started_at,ended_at:$ended_at,exit_code:$exit_code}' >> "$geo_r20_live/network-events.jsonl"
    printf '%s Q%s HTTP %s\n' "$geo_r20_provider" "$geo_r20_number" "$geo_r20_http"
  done
done < "$geo_r20_root/queries.txt"
