#!/bin/bash
# Fetch raw GoatCounter stats with curl into <out-dir> (hits.json, toprefs.json,
# total.json, meta.json). For hosts whose compute nodes cannot reach GoatCounter:
# fetch here (light network I/O, no Python), then summarise anywhere with
#   geo_eval ood --goatcounter <code> --input-dir <out-dir> --log <instance>/ood.jsonl
# The token is read from its file into the request header only; it is never printed.
#   geo/scripts/fetch_goatcounter.sh <site-code> <token-file> <days> <out-dir>
set -euo pipefail
CODE="${1:?usage: fetch_goatcounter.sh <site-code> <token-file> <days> <out-dir>}"
TOKEN_FILE="${2/#\~/$HOME}"
DAYS="${3:-7}"
OUT="${4:?out-dir}"
mkdir -p "$OUT"
BASE="https://$CODE.goatcounter.com/api/v0"
END="$(date -u +%Y-%m-%dT%H:00:00Z)"
START="$(date -u -d "$DAYS days ago" +%Y-%m-%dT%H:00:00Z)"
fetch() {
  local name="$1" query="$2" code
  code=$(curl -sS -o "$OUT/$name.json" -w '%{http_code}' --max-time 60 \
    -H "Authorization: Bearer $(cat "$TOKEN_FILE")" "$BASE/$query")
  [ "$code" = 200 ] || { echo "GoatCounter $name: HTTP $code" >&2; exit 1; }
}
fetch hits "stats/hits?start=$START&end=$END&daily=true"
fetch toprefs "stats/toprefs?start=$START&end=$END"
fetch total "stats/total?start=$START&end=$END"
printf '{"site": "%s", "days": %s, "start": "%s", "end": "%s"}\n' "$CODE" "$DAYS" "$START" "$END" > "$OUT/meta.json"
echo "saved GoatCounter stats ($START .. $END) to $OUT"
