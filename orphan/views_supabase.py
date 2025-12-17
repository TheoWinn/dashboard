import os
from dotenv import load_dotenv
import psycopg2

load_dotenv()
DB_URL = os.environ["DATABASE_URL"]

# this creates the schema that holds the dashboard views
create_dashboard_schema = """
CREATE SCHEMA IF NOT EXISTS dashboard;
"""

# this creates a role that will own the dashboard views, it is granted minimal access to the underlying data
# create_ownership_dashboard = """
# DO $$
# BEGIN
#   CREATE ROLE dashboard_owner NOLOGIN;
# EXCEPTION
#   WHEN duplicate_object THEN
#     NULL; -- do nothing, role already exists
# END
# $$;
# """

# this grants the postgres user membership in the dashboard_owner role, so it can create and manage views
# grant_dashboard_owner_membership_to_postgres = """
# GRANT dashboard_owner TO postgres;
# """

# this grants the dashboard_owner role the ability to create objects in the dashboard schema
# grant_dashboard_owner_schema_privs = """
# GRANT USAGE, CREATE ON SCHEMA dashboard TO dashboard_owner;
# """

# remove any public access to the private schema
# remove_public_access_private = """
# REVOKE ALL ON SCHEMA private FROM anon, authenticated;
# REVOKE ALL ON ALL TABLES IN SCHEMA private FROM anon, authenticated;
# REVOKE ALL ON ALL SEQUENCES IN SCHEMA private FROM anon, authenticated;
# REVOKE ALL ON ALL FUNCTIONS IN SCHEMA private FROM anon, authenticated;
# """

# grant the dashboard_owner role minimal access to the underlying private data needed for the views
# grant_minimal_private_access_to_dashboard_owner = """
# GRANT USAGE ON SCHEMA private TO dashboard_owner;
# REVOKE ALL ON private.speakers FROM dashboard_owner;
# GRANT SELECT (speaker_id, speaker_name)
# ON private.speakers
# TO dashboard_owner;
# """

# allow the anon and authenticated roles to access the dashboard schema (views will be restricted later)
grant_public_usage_dashboard = """
GRANT USAGE ON SCHEMA dashboard TO anon, authenticated;
REVOKE CREATE ON SCHEMA dashboard FROM anon, authenticated;
"""

# create a test view in the dashboard schema (with securtiy_invoker)
create_test_view = """
CREATE OR REPLACE VIEW dashboard.test WITH (SECURITY_INVOKER = TRUE)  AS
SELECT speaker_id, speaker_name
FROM private.speakers
LIMIT 10;
"""

# set the owner of the test view to the dashboard_owner role
# set_test_owner = """
# ALTER VIEW dashboard.test OWNER TO dashboard_owner;
# """

# restrict access to the test view to only allow anon role to SELECT
restrict_and_grant_view = """
REVOKE ALL ON dashboard.test FROM PUBLIC;
REVOKE ALL ON dashboard.test FROM anon, authenticated;
GRANT SELECT ON dashboard.test TO anon;
"""

# make the test view read-only for all roles
make_view_read_only = """
REVOKE INSERT, UPDATE, DELETE, TRUNCATE, REFERENCES, TRIGGER
ON dashboard.test
FROM dashboard_owner, anon, authenticated;
"""

# cleanup any previous broad grants on the dashboard schema
cleanup_dashboard_schema_grants = """
REVOKE ALL ON ALL TABLES IN SCHEMA dashboard FROM anon, authenticated;
REVOKE ALL ON ALL SEQUENCES IN SCHEMA dashboard FROM anon, authenticated;
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA dashboard FROM anon, authenticated;
"""

with psycopg2.connect(DB_URL) as conn:
    with conn.cursor() as cur:
        cur.execute(create_dashboard_schema)
        # cur.execute(create_ownership_dashboard)
        # cur.execute(grant_dashboard_owner_membership_to_postgres)
        # cur.execute(grant_dashboard_owner_schema_privs)

        # cur.execute(remove_public_access_private)
        # cur.execute(grant_minimal_private_access_to_dashboard_owner)

        cur.execute(grant_public_usage_dashboard)

        cur.execute(create_test_view)
        # cur.execute(set_test_owner)

        # cleanup any previous broad grants, then set the precise desired permissions
        cur.execute(cleanup_dashboard_schema_grants)
        cur.execute(make_view_read_only)
        cur.execute(restrict_and_grant_view)

    conn.commit()
