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
"""

# ownership of functions to dashboard_owner
ownership_functions = """
ALTER FUNCTION dashboard_internal._fn_topics_read() OWNER TO dashboard_owner;
ALTER FUNCTION dashboard_internal._fn_speeches_date_read() OWNER TO dashboard_owner;
"""

# create view in dashboard schema from security definer function
create_views = """
-- topics view
CREATE OR REPLACE VIEW dashboard.topics_view AS
SELECT * 
FROM dashboard_internal._fn_topics_read();

-- speeches with date view
CREATE OR REPLACE VIEW dashboard.speeches_date_view AS
SELECT *
FROM dashboard_internal._fn_speeches_date_read();
"""

# ownership of views to dashboard_owner
ownership_views = """
ALTER VIEW dashboard.topics_view OWNER TO dashboard_owner;
ALTER VIEW dashboard.speeches_date_view OWNER TO dashboard_owner;
"""

# give dashboard_reader minimal rights to access dashboard schema
minimal_rights = """
GRANT USAGE ON SCHEMA dashboard TO dashboard_reader;
REVOKE ALL ON dashboard.topics_view FROM PUBLIC, anon, authenticated;
GRANT SELECT ON dashboard.topics_view TO dashboard_reader;
REVOKE ALL ON dashboard.speeches_date_view FROM PUBLIC, anon, authenticated;
GRANT SELECT ON dashboard.speeches_date_view TO dashboard_reader;
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
