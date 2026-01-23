#!/usr/bin/env bash
set -euo pipefail

if [[ -f .env ]]; then
    set -a
    source .env
    set +a
else 
    echo "Missing .env file" >&2
    exit 1
fi

# check which packages are there for nice printing
pretty() {
  if command -v jq >/dev/null 2>&1; then
    jq .
  elif command -v python3 >/dev/null 2>&1; then
    python3 -m json.tool
  elif command -v python >/dev/null 2>&1; then
    python -m json.tool
  else
    cat
  fi
}

BASE_URL="https://${PROJECT_ID}.supabase.co/rest/v1"
HDRS=(
  -H "apikey: ${ANON_KEY}"
  -H "Authorization: Bearer ${ANON_KEY}"
  -H "Accept-Profile: dashboard"
)

OUTDIR="api_demo_output"
mkdir -p "$OUTDIR"
TS="$(date +%Y%m%d_%H%M%S)"
OUTFILE="${OUTDIR}/demo_${TS}.log"

echo "top 7 most salient topics in Bundestag" | tee -a "$OUTFILE"
curl -fsS -G "${BASE_URL}/topics_view" \
  -d "select=topic_label,bt_normalized_perc,ts_normalized_perc,mismatch_ppoints,mismatch_log_ratio" \
  -d "order=bt_normalized_perc.desc" \
  -d "limit=7" \
  "${HDRS[@]}" \
| pretty | tee -a "$OUTFILE"

echo "top 7 most salient topics in talk shows" | tee -a "$OUTFILE"
curl -fsS -G "${BASE_URL}/topics_view" \
  -d "select=topic_label,ts_normalized_perc,bt_normalized_perc,mismatch_ppoints,mismatch_log_ratio" \
  -d "order=ts_normalized_perc.desc" \
  -d "limit=7" \
  "${HDRS[@]}" \
| pretty | tee -a "$OUTFILE"

echo "top 5 topics with higher salience in Bundestag than talk shows" | tee -a "$OUTFILE"
curl -fsS -G "${BASE_URL}/topics_view" \
  -d "select=topic_label,bt_normalized_perc,ts_normalized_perc,mismatch_ppoints,mismatch_log_ratio" \
  -d "order=mismatch_ppoints.desc" \
  -d "limit=5" \
  "${HDRS[@]}" \
| pretty | tee -a "$OUTFILE"

echo "top 5 topics with higher salience in talk shows than Bundestag" | tee -a "$OUTFILE"
curl -fsS -G "${BASE_URL}/topics_view" \
  -d "select=topic_label,ts_normalized_perc,bt_normalized_perc,mismatch_ppoints,mismatch_log_ratio" \
  -d "order=mismatch_ppoints.asc" \
  -d "limit=5" \
  "${HDRS[@]}" \
| pretty | tee -a "$OUTFILE"

echo "top 5 topics of AfD in Bundestag" | tee -a "$OUTFILE"
curl -fsS -G "${BASE_URL}/topics_duration_by_party_view" \
  -d "select=topic_label,topic_duration_per_party" \
  -d "order=topic_duration_per_party.desc" \
  -d "speaker_party=eq.AfD" \
  -d "limit=5" \
  "${HDRS[@]}" \
| pretty | tee -a "$OUTFILE"

echo "top 5 topics of Die Linke in Bundestag" | tee -a "$OUTFILE"
curl -fsS -G "${BASE_URL}/topics_duration_by_party_view" \
  -d "select=topic_label,topic_duration_per_party" \
  -d "order=topic_duration_per_party.desc" \
  --data-urlencode "speaker_party=eq.Die Linke" \
  -d "limit=5" \
  "${HDRS[@]}" \
| pretty | tee -a "$OUTFILE"

echo "top 5 topics of BÜNDNIS 90/DIE GRÜNEN in Bundestag" | tee -a "$OUTFILE"
curl -fsS -G "${BASE_URL}/topics_duration_by_party_view" \
  -d "select=topic_label,topic_duration_per_party" \
  -d "order=topic_duration_per_party.desc" \
  --data-urlencode "speaker_party=eq.BÜNDNIS 90/DIE GRÜNEN" \
  -d "limit=5" \
  "${HDRS[@]}" \
| pretty | tee -a "$OUTFILE"

echo "peak window for topic Middle East Conflict in Bundestag" | tee -a "$OUTFILE"
curl -fsS -G "${BASE_URL}/topics_view_4w" \
  -d "select=window_start,window_end,topic_label,bt_normalized_perc,ts_normalized_perc,mismatch_ppoints" \
  --data-urlencode "topic_label=eq.Middle East Conflict" \
  -d "bt_normalized_perc=not.is.null" \
  -d "order=bt_normalized_perc.desc" \
  -d "limit=1" \
  "${HDRS[@]}" \
| pretty | tee -a "$OUTFILE"

echo "peak window for topic Middle East Conflict in Talkshow" | tee -a "$OUTFILE"
curl -fsS -G "${BASE_URL}/topics_view_4w" \
  -d "select=window_start,window_end,topic_label,ts_normalized_perc,bt_normalized_perc,mismatch_ppoints" \
  --data-urlencode "topic_label=eq.Middle East Conflict" \
  -d "ts_normalized_perc=not.is.null" \
  -d "order=ts_normalized_perc.desc" \
  -d "limit=1" \
  "${HDRS[@]}" \
| pretty | tee -a "$OUTFILE"

echo ""
echo "Saved full output to: ${OUTFILE}"