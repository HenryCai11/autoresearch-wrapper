#!/bin/bash
# Network-only collector. Headers go to curl stdin and are never saved or echoed.
set -euo pipefail
set +x
test -n "${TAVILY_API_KEY:?Missing inherited Tavily environment}"
test -n "${EXA_API_KEY:?Missing inherited Exa environment}"
geo_r21_root=/scratch/henrycai/geo-runs/eau-r21-20261020
geo_r21_live="$geo_r21_root/r21-live"
test -s "$geo_r21_live/verified-before.txt"
test ! -e "$geo_r21_live/network-events.jsonl"
geo_r21_index=0
while IFS= read -r geo_r21_query; do
  geo_r21_index=$((geo_r21_index + 1))
  geo_r21_number="$(printf '%02d' "$geo_r21_index")"
  for geo_r21_provider in tavily exa; do
    geo_r21_request="$geo_r21_live/$geo_r21_provider-raw/$geo_r21_number-request.json"
    geo_r21_response="$geo_r21_live/$geo_r21_provider-raw/$geo_r21_number.json"
    if [ "$geo_r21_provider" = tavily ]; then
      jq -nc --arg query "$geo_r21_query" '{query:$query,topic:"general",search_depth:"basic",max_results:10,include_answer:false,include_raw_content:false,include_images:false}' > "$geo_r21_request"
      geo_r21_endpoint=https://api.tavily.com/search
    else
      jq -nc --arg query "$geo_r21_query" '{query:$query,type:"auto",numResults:10,contents:{highlights:true}}' > "$geo_r21_request"
      geo_r21_endpoint=https://api.exa.ai/search
    fi
    geo_r21_started="$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
    geo_r21_code=0
    if [ "$geo_r21_provider" = tavily ]; then
      geo_r21_http="$(printf 'header = "Authorization: Bearer %s"\n' "$TAVILY_API_KEY" | curl --config - --silent --show-error --max-time 60 --header 'Content-Type: application/json' --data-binary "@$geo_r21_request" --output "$geo_r21_response" --write-out '%{http_code}' "$geo_r21_endpoint")" || geo_r21_code=$?
    else
      geo_r21_http="$(printf 'header = "x-api-key: %s"\n' "$EXA_API_KEY" | curl --config - --silent --show-error --max-time 60 --header 'Content-Type: application/json' --data-binary "@$geo_r21_request" --output "$geo_r21_response" --write-out '%{http_code}' "$geo_r21_endpoint")" || geo_r21_code=$?
    fi
    geo_r21_ended="$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
    jq -nc --arg query "$geo_r21_query" --arg provider "$geo_r21_provider" --arg http "$geo_r21_http" --arg started_at "$geo_r21_started" --arg ended_at "$geo_r21_ended" --argjson exit_code "$geo_r21_code" '{query:$query,provider:$provider,http:$http,started_at:$started_at,ended_at:$ended_at,exit_code:$exit_code}' >> "$geo_r21_live/network-events.jsonl"
    printf '%s Q%s HTTP %s\n' "$geo_r21_provider" "$geo_r21_number" "$geo_r21_http"
  done
done < "$geo_r21_root/queries.txt"
