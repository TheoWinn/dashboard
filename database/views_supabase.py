import os
from dotenv import load_dotenv
import psycopg2

load_dotenv()
DB_URL = os.environ["DATABASE_URL"]

# # check current role
# check = """
# SELECT current_user, session_user, current_role;
# """

# create schemas
create_schemas = """
CREATE SCHEMA IF NOT EXISTS dashboard;
CREATE SCHEMA IF NOT EXISTS dashboard_internal;
"""

# create roles
create_roles = """
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'dashboard_owner') THEN
        CREATE ROLE dashboard_owner NOINHERIT;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'dashboard_reader') THEN
        CREATE ROLE dashboard_reader NOINHERIT;
    END IF;
END;
$$;
"""

# ownership of schemas
ownership_schemas = """
ALTER SCHEMA dashboard OWNER TO dashboard_owner;
ALTER SCHEMA dashboard_internal OWNER TO dashboard_owner;
"""

# lock down schemas
lockdown_schemas = """
REVOKE ALL ON SCHEMA dashboard_internal FROM PUBLIC, anon, authenticated;
REVOKE ALL ON SCHEMA private FROM PUBLIC, anon, authenticated;
REVOKE ALL ON SCHEMA dashboard FROM PUBLIC, anon, authenticated;
"""

# grant select on private.speakers to dashboard_owner
grant_select_private = """
GRANT SELECT ON private.speeches TO dashboard_owner;
GRANT SELECT ON private.topics TO dashboard_owner;
GRANT SELECT ON private.files TO dashboard_owner;
"""

# security definer function in dashboard_internal (are executed with owners privileges)
sd_functions = """
-- topics read function
CREATE OR REPLACE FUNCTION dashboard_internal._fn_topics_read()
RETURNS TABLE (
    topic_id INTEGER,
    topic_keywords TEXT,
    topic_label TEXT,
    topic_duration INTERVAL,
    topic_duration_bt INTERVAL,
    topic_duration_ts INTERVAL
)
LANGUAGE sql
SECURITY DEFINER SET search_path = pg_catalog, private
STABLE
AS $$
    SELECT * 
    FROM private.topics;
$$;
REVOKE ALL ON FUNCTION dashboard_internal._fn_topics_read() FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION dashboard_internal._fn_topics_read() TO dashboard_reader;

-- speeches with date read function
CREATE OR REPLACE FUNCTION dashboard_internal._fn_speeches_date_read()
RETURNS TABLE (
    speech_id BIGINT,
    source TEXT,
    speech_duration INTERVAL,
    speech_date DATE,
    topic INTEGER
)
LANGUAGE sql
SECURITY DEFINER SET search_path = pg_catalog, private
STABLE
AS $$
    SELECT s.speech_id, f.source, s.speech_duration, f.file_date AS speech_date, s.topic
    FROM private.speeches AS s
    JOIN private.files AS f
    ON s.file = f.file_id;
$$;
REVOKE ALL ON FUNCTION dashboard_internal._fn_speeches_date_read() FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION dashboard_internal._fn_speeches_date_read() TO dashboard_reader;

-- function for windowed metrics
CREATE OR REPLACE FUNCTION dashboard_internal._fn_topics_metrics_all_xweek_windows(
    p_year         int,
    p_window_weeks int
)
RETURNS TABLE (
    window_start date,
    window_end   date,

    topic_id integer,
    topic_label text,
    topic_keywords text,

    topic_duration interval,
    topic_duration_bt interval,
    topic_duration_ts interval,

    bt_normalized_perc numeric,
    ts_normalized_perc numeric
)
LANGUAGE sql
SECURITY DEFINER
SET search_path = pg_catalog, private
STABLE
AS $$
WITH params AS (
  SELECT
    make_date(p_year, 1, 1)::date         AS start_date,
    make_date(p_year + 1, 1, 1)::date     AS end_date,       -- exclusive end
    (p_window_weeks || ' weeks')::interval AS step
),
windows AS (
  SELECT
    gs::date AS window_start,
    LEAST((gs + p.step)::date, p.end_date) AS window_end
  FROM params p
  CROSS JOIN generate_series(p.start_date, p.end_date - p.step, p.step) AS gs
),
speech_rows AS (
  SELECT
    w.window_start,
    w.window_end,
    s.topic AS topic_id,
    f.source,
    s.speech_duration
  FROM windows w
  JOIN private.files f
    ON f.file_date >= w.window_start
   AND f.file_date <  w.window_end
  JOIN private.speeches s
    ON s.file = f.file_id
  WHERE s.topic IS NOT NULL
),
agg AS (
  SELECT
    window_start,
    window_end,
    topic_id,
    SUM(speech_duration) AS topic_duration,
    SUM(speech_duration) FILTER (WHERE source = 'bundestag') AS topic_duration_bt,
    SUM(speech_duration) FILTER (WHERE source = 'talkshow')  AS topic_duration_ts
  FROM speech_rows
  GROUP BY 1,2,3
),
base AS (
  SELECT
    a.window_start,
    a.window_end,
    t.topic_id,
    t.topic_label,
    t.topic_keywords,
    a.topic_duration,
    a.topic_duration_bt,
    a.topic_duration_ts,
    EXTRACT(EPOCH FROM a.topic_duration_bt)::numeric AS bt_seconds,
    EXTRACT(EPOCH FROM a.topic_duration_ts)::numeric AS ts_seconds
  FROM agg a
  JOIN private.topics t ON t.topic_id = a.topic_id
),
norm AS (
  SELECT
    *,
    bt_seconds / NULLIF(SUM(bt_seconds) OVER (PARTITION BY window_start), 0) AS bt_normalized,
    ts_seconds / NULLIF(SUM(ts_seconds) OVER (PARTITION BY window_start), 0) AS ts_normalized
  FROM base
)
SELECT
  window_start,
  window_end,

  topic_id,
  topic_label,
  topic_keywords,

  topic_duration,
  topic_duration_bt,
  topic_duration_ts,

  (bt_normalized * 100) AS bt_normalized_perc,
  (ts_normalized * 100) AS ts_normalized_perc
FROM norm
ORDER BY window_start, topic_id;
$$;

REVOKE ALL ON FUNCTION dashboard_internal._fn_topics_metrics_all_xweek_windows(int,int)
  FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION dashboard_internal._fn_topics_metrics_all_xweek_windows(int,int)
  TO dashboard_reader;

-- public wrapper function for windowed metrics
CREATE OR REPLACE FUNCTION dashboard.topics_metrics_all_xweek_windows(
  p_year int,
  p_window_weeks int
)
RETURNS TABLE (
  window_start date,
  window_end   date,

  topic_id integer,
  topic_label text,
  topic_keywords text,

  topic_duration interval,
  topic_duration_bt interval,
  topic_duration_ts interval,

  bt_normalized_perc numeric,
  ts_normalized_perc numeric
)
LANGUAGE sql
SECURITY DEFINER
SET search_path = pg_catalog  -- keep tight; we schema-qualify everything
STABLE
AS $$
  SELECT *
  FROM dashboard_internal._fn_topics_metrics_all_xweek_windows(p_year, p_window_weeks);
$$;

REVOKE ALL ON FUNCTION dashboard.topics_metrics_all_xweek_windows(int,int)
  FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION dashboard.topics_metrics_all_xweek_windows(int,int)
  TO dashboard_reader;
"""

# ownership of functions to dashboard_owner
ownership_functions = """
ALTER FUNCTION dashboard_internal._fn_topics_read() OWNER TO dashboard_owner;
ALTER FUNCTION dashboard_internal._fn_speeches_date_read() OWNER TO dashboard_owner;
ALTER FUNCTION dashboard_internal._fn_topics_metrics_all_xweek_windows(int,int) OWNER TO dashboard_owner;
ALTER FUNCTION dashboard.topics_metrics_all_xweek_windows(int,int) OWNER TO dashboard_owner;
"""

# create view in dashboard schema from security definer function
create_views = """
-- topics view
CREATE OR REPLACE VIEW dashboard.topics_view AS
WITH base AS (
  SELECT
    topic_id,
    topic_label,
    topic_keywords,
    topic_duration,
    topic_duration_bt,
    topic_duration_ts,

    -- convert intervals to seconds (numeric)
    EXTRACT(EPOCH FROM topic_duration_bt)::numeric AS bt_seconds,
    EXTRACT(EPOCH FROM topic_duration_ts)::numeric AS ts_seconds
  FROM dashboard_internal._fn_topics_read()
),
norm AS (
  SELECT
    *,
    bt_seconds / NULLIF(SUM(bt_seconds) OVER (), 0) AS bt_normalized,
    ts_seconds / NULLIF(SUM(ts_seconds) OVER (), 0) AS ts_normalized
  FROM base
)
SELECT
  topic_id,
  topic_label,
  topic_keywords,
  topic_duration,
  topic_duration_bt,
  topic_duration_ts,
  (bt_normalized*100) AS bt_normalized_perc,
  (ts_normalized*100) AS ts_normalized_perc,
  (bt_normalized / NULLIF(bt_normalized + ts_normalized, 0))*100 AS bt_share,
  (ts_normalized / NULLIF(bt_normalized + ts_normalized, 0))*100 AS ts_share,
  (bt_normalized - ts_normalized)*100 AS mismatch_ppoints,
  log((bt_normalized+0.0000001)/(ts_normalized+0.0000001)) AS mismatch_log_ratio
FROM norm;

-- speeches with date view
CREATE OR REPLACE VIEW dashboard.speeches_date_view AS
SELECT *
FROM dashboard_internal._fn_speeches_date_read();

-- 4-week windowed metrics view
CREATE OR REPLACE VIEW dashboard.topics_view_2025_4w AS
SELECT *
FROM dashboard_internal._fn_topics_metrics_all_xweek_windows(2025, 4);
"""

# ownership of views to dashboard_owner
ownership_views = """
ALTER VIEW dashboard.topics_view OWNER TO dashboard_owner;
ALTER VIEW dashboard.speeches_date_view OWNER TO dashboard_owner;
ALTER VIEW dashboard.topics_view_2025_4w OWNER TO dashboard_owner;
"""

# give dashboard_reader minimal rights to access dashboard schema
minimal_rights = """
GRANT USAGE ON SCHEMA dashboard TO dashboard_reader;
REVOKE ALL ON dashboard.topics_view FROM PUBLIC, anon, authenticated;
GRANT SELECT ON dashboard.topics_view TO dashboard_reader;
REVOKE ALL ON dashboard.speeches_date_view FROM PUBLIC, anon, authenticated;
GRANT SELECT ON dashboard.speeches_date_view TO dashboard_reader;
REVOKE ALL ON dashboard.topics_view_2025_4w FROM PUBLIC, anon, authenticated;
GRANT SELECT ON dashboard.topics_view_2025_4w TO dashboard_reader;
"""

# give anon dashboard_reader role for read-only access
grant_anon_role = """
GRANT dashboard_reader TO anon;"""

with psycopg2.connect(DB_URL) as conn:
    with conn.cursor() as cur:
        cur.execute(create_schemas)
        cur.execute(create_roles)
        cur.execute(ownership_schemas)
        cur.execute(lockdown_schemas)
        cur.execute(grant_select_private)
        cur.execute(sd_functions)
        cur.execute(ownership_functions)
        cur.execute(create_views)
        cur.execute(ownership_views)
        cur.execute(minimal_rights)
        cur.execute(grant_anon_role)
        
    conn.commit()
