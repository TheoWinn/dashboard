import os
from dotenv import load_dotenv
import psycopg2

load_dotenv()
DB_URL = os.environ["DATABASE_URL"]

create_dashboard_schema = """
CREATE SCHEMA IF NOT EXISTS dashboard;
"""

create_ownership_dashboard = """
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'dashboard_owner') THEN
    CREATE ROLE dashboard_owner NOLOGIN;
  END IF;
END
$$;
"""

grant_dashboard_owner_membership_to_postgres = """
GRANT dashboard_owner TO postgres;
"""

# Needed so the role can be the *owner* of objects in the schema
grant_dashboard_owner_schema_privs = """
GRANT USAGE, CREATE ON SCHEMA dashboard TO dashboard_owner;
"""

# Lock down private for normal API roles
remove_public_access_private = """
REVOKE ALL ON SCHEMA private FROM anon, authenticated;
REVOKE ALL ON ALL TABLES IN SCHEMA private FROM anon, authenticated;
REVOKE ALL ON ALL SEQUENCES IN SCHEMA private FROM anon, authenticated;
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA private FROM anon, authenticated;
"""

# Ensure dashboard_owner has ONLY minimal READ access in private
grant_minimal_private_access_to_dashboard_owner = """
GRANT USAGE ON SCHEMA private TO dashboard_owner;

-- Remove any accidental broader grants first (idempotent cleanup)
REVOKE ALL ON private.speakers FROM dashboard_owner;

-- Then grant only what the view needs
GRANT SELECT (speaker_id, speaker_name)
ON private.speakers
TO dashboard_owner;
"""

# Allow clients to reference objects in dashboard schema, but not create there
grant_public_usage_dashboard = """
GRANT USAGE ON SCHEMA dashboard TO anon, authenticated;
REVOKE CREATE ON SCHEMA dashboard FROM anon, authenticated;
"""

create_test_view = """
CREATE OR REPLACE VIEW dashboard.test AS
SELECT speaker_id, speaker_name
FROM private.speakers
LIMIT 10;
"""

set_test_owner = """
ALTER VIEW dashboard.test OWNER TO dashboard_owner;
"""

# Option 2: explicitly restrict access to the privileged view
restrict_and_grant_view = """
REVOKE ALL ON dashboard.test FROM PUBLIC;
REVOKE ALL ON dashboard.test FROM anon, authenticated;
GRANT SELECT ON dashboard.test TO anon;
"""

# ✅ NEW: make the view surface read-only (avoid any accidental DML grants)
# (Views generally aren't writable anyway, but this cleans up privileges and matches intent.)
make_view_read_only = """
REVOKE INSERT, UPDATE, DELETE, TRUNCATE, REFERENCES, TRIGGER
ON dashboard.test
FROM dashboard_owner, anon, authenticated;
"""

# ✅ NEW: clean up any accidental grants on ALL objects in dashboard schema
# This prevents "dashboard_owner has INSERT/UPDATE/..." from previous runs.
cleanup_dashboard_schema_grants = """
REVOKE ALL ON ALL TABLES IN SCHEMA dashboard FROM anon, authenticated;
REVOKE ALL ON ALL SEQUENCES IN SCHEMA dashboard FROM anon, authenticated;
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA dashboard FROM anon, authenticated;
"""

with psycopg2.connect(DB_URL) as conn:
    with conn.cursor() as cur:
        cur.execute(create_dashboard_schema)
        cur.execute(create_ownership_dashboard)
        cur.execute(grant_dashboard_owner_membership_to_postgres)
        cur.execute(grant_dashboard_owner_schema_privs)

        cur.execute(remove_public_access_private)
        cur.execute(grant_minimal_private_access_to_dashboard_owner)

        cur.execute(grant_public_usage_dashboard)

        cur.execute(create_test_view)
        cur.execute(set_test_owner)

        # cleanup any previous broad grants, then set the precise desired permissions
        cur.execute(cleanup_dashboard_schema_grants)
        cur.execute(make_view_read_only)
        cur.execute(restrict_and_grant_view)

    conn.commit()
