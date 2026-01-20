from dotenv import load_dotenv
from supabase import create_client
import os

load_dotenv()
supabase = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_ANON_KEY"])


# example supabase syntax
resp = supabase.schema("dashboard").table("topics_view").select("*").eq("topic_id", "1").execute()
print(resp.data)

resp = supabase.schema("dashboard").table("topics_view_2025_4w").select("*").execute()
print(resp.data)

resp = supabase.schema("dashboard").rpc("topics_metrics_all_xweek_windows", {"p_year": 2025, "p_window_weeks": 2}).select("*").execute()
print(resp.data)

# example curl:
"""
curl 'https://<PROJECT_REF>.supabase.co/rest/v1/topics_view' \
  -H "apikey: <SUPABASE_ANON_KEY>" \
  -H "Authorization: Bearer <SUPABASE_ANON_KEY>" \
  -H "Accept-Profile: dashboard"
"""

# get api documentation:
"""
curl 'https://<PROJECT_REF>.supabase.co/rest/v1/' \
  -H "apikey: <SUPABASE_ANON_KEY>" \
  -H "Authorization: Bearer <SUPABASE_ANON_KEY>" \
  -H "Accept-Profile: dashboard" \
  -H "Accept: application/openapi+json"
"""