from db_utils import fill_db, views_db
from dotenv import load_dotenv
import os
import psycopg2
from supabase import create_client

load_dotenv()
DB_URL = os.environ["DATABASE_URL"]

# path to csv file?
# fill_db(DB_URL, "path_to_csv")

with psycopg2.connect(DB_URL) as conn:
        with conn.cursor() as cur:
            cur.execute("drop schema if exists dashboard_internal cascade;")
            cur.execute("drop schema if exists dashboard cascade;")
        conn.commit()

views_db(DB_URL)

supabase = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_ANON_KEY"])
resp = supabase.schema("dashboard").rpc("topics_metrics_all_xweek_windows", {"p_year": 2025, "p_window_weeks": 4}).select("topic_duration_ts").eq("topic_id", "1").execute()
print(resp.data)
