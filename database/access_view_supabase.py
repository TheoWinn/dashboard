from dotenv import load_dotenv
from supabase import create_client
import os

load_dotenv()
supabase = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_ANON_KEY"])

resp = supabase.schema("dashboard").table("topics_view").select("*").eq("topic_id", "-1").execute()
print(resp.data)

resp = supabase.schema("dashboard").table("topics_view_2025_4w").select("window_start").eq("topic_id", "1").execute()
print(resp.data)

resp = supabase.schema("dashboard").rpc("topics_metrics_all_xweek_windows", {"p_year": 2025, "p_window_weeks": 4}).select("window_start").eq("topic_id", "1").execute()
print(resp.data)

# resp = supabase.schema("dashboard").table("speeches_date_view").select("*").execute()
# print(resp.data)