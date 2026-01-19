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

# get 10 most salient topics in Bundestag
curl -sS -G "https://${PROJECT_ID}.supabase.co/rest/v1/topics_view" \
  -d "select=topic_label,topic_duration_bt,bt_normalized_perc,mismatch_ppoints,mismatch_log_ratio" \
  -d "order=bt_normalized_perc.desc" \
  -d "limit=10" \
  -H "apikey: ${ANON_KEY}" \
  -H "Authorization: Bearer ${ANON_KEY}" \
  -H "Accept-Profile: dashboard" \
| python3 -m json.tool