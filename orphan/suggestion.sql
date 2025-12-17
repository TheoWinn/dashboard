-- 0. Create schema and roles if missing
CREATE SCHEMA IF NOT EXISTS dashboard;

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

-- 1. Revoke any existing public access to private schema/tables
REVOKE ALL ON SCHEMA private FROM PUBLIC;
REVOKE ALL ON SCHEMA private FROM anon;
REVOKE ALL ON SCHEMA private FROM authenticated;

REVOKE ALL ON private.speakers FROM PUBLIC;
REVOKE ALL ON private.speakers FROM anon;
REVOKE ALL ON private.speakers FROM authenticated;

REVOKE ALL ON private.files FROM PUBLIC;
REVOKE ALL ON private.files FROM anon;
REVOKE ALL ON private.files FROM authenticated;

REVOKE ALL ON private.topics FROM PUBLIC;
REVOKE ALL ON private.topics FROM anon;
REVOKE ALL ON private.topics FROM authenticated;

REVOKE ALL ON private.speeches FROM PUBLIC;
REVOKE ALL ON private.speeches FROM anon;
REVOKE ALL ON private.speeches FROM authenticated;

-- 2. Create SECURITY DEFINER functions that expose allowed columns
-- speakers
CREATE OR REPLACE FUNCTION dashboard._fn_speakers_read()
RETURNS TABLE (
  speaker_id bigint,
  speaker_name text,
  speaker_party text
)
LANGUAGE sql
SECURITY DEFINER
STABLE
AS $$
  SELECT speaker_id, speaker_name, speaker_party
  FROM private.speakers;
$$;
-- restrict default EXECUTE and grant to dashboard_owner temporarily so ownership change works
REVOKE ALL ON FUNCTION dashboard._fn_speakers_read() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION dashboard._fn_speakers_read() TO dashboard_owner;

-- files
CREATE OR REPLACE FUNCTION dashboard._fn_files_read()
RETURNS TABLE (
  file_id bigint,
  file_name text,
  file_date date,
  file_year integer,
  source text
)
LANGUAGE sql
SECURITY DEFINER
STABLE
AS $$
  SELECT file_id, file_name, file_date, file_year, source
  FROM private.files;
$$;
REVOKE ALL ON FUNCTION dashboard._fn_files_read() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION dashboard._fn_files_read() TO dashboard_owner;

-- topics
CREATE OR REPLACE FUNCTION dashboard._fn_topics_read()
RETURNS TABLE (
  topic_id integer,
  topic_keywords text,
  topic_label text,
  topic_duration interval,
  topic_duration_bt interval,
  topic_duration_ts interval
)
LANGUAGE sql
SECURITY DEFINER
STABLE
AS $$
  SELECT topic_id, topic_keywords, topic_label, topic_duration, topic_duration_bt, topic_duration_ts
  FROM private.topics;
$$;
REVOKE ALL ON FUNCTION dashboard._fn_topics_read() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION dashboard._fn_topics_read() TO dashboard_owner;

-- speeches (omit speech_text)
CREATE OR REPLACE FUNCTION dashboard._fn_speeches_read()
RETURNS TABLE (
  speech_id bigint,
  speech_key text,
  speech_duration interval,
  file bigint,
  speaker bigint,
  topic integer
)
LANGUAGE sql
SECURITY DEFINER
STABLE
AS $$
  SELECT speech_id, speech_key, speech_duration, file, speaker, topic
  FROM private.speeches;
$$;
REVOKE ALL ON FUNCTION dashboard._fn_speeches_read() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION dashboard._fn_speeches_read() TO dashboard_owner;

-- 3. Create views that select from the functions (these will be the frontend surface)
CREATE OR REPLACE VIEW dashboard.speakers_view AS
SELECT * FROM dashboard._fn_speakers_read();

CREATE OR REPLACE VIEW dashboard.files_view AS
SELECT * FROM dashboard._fn_files_read();

CREATE OR REPLACE VIEW dashboard.topics_view AS
SELECT * FROM dashboard._fn_topics_read();

CREATE OR REPLACE VIEW dashboard.speeches_view AS
SELECT * FROM dashboard._fn_speeches_read();

-- 4. Make dashboard_owner own the functions and views
-- (If objects are already owned by someone else, ALTER OWNER will succeed only if you have privileges)
ALTER FUNCTION dashboard._fn_speakers_read() OWNER TO dashboard_owner;
ALTER FUNCTION dashboard._fn_files_read() OWNER TO dashboard_owner;
ALTER FUNCTION dashboard._fn_topics_read() OWNER TO dashboard_owner;
ALTER FUNCTION dashboard._fn_speeches_read() OWNER TO dashboard_owner;

ALTER VIEW dashboard.speakers_view OWNER TO dashboard_owner;
ALTER VIEW dashboard.files_view OWNER TO dashboard_owner;
ALTER VIEW dashboard.topics_view OWNER TO dashboard_owner;
ALTER VIEW dashboard.speeches_view OWNER TO dashboard_owner;

-- 5. Revoke EXECUTE on functions from PUBLIC/anon/authenticated to be safe,
--    and grant EXECUTE only to dashboard_owner (so only the owner/view can use underlying privileges)
REVOKE ALL ON FUNCTION dashboard._fn_speakers_read() FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION dashboard._fn_files_read() FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION dashboard._fn_topics_read() FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION dashboard._fn_speeches_read() FROM PUBLIC, anon, authenticated;

-- 6. Secure schema usage and grant only necessary privileges on views to dashboard_reader
REVOKE ALL ON SCHEMA dashboard FROM PUBLIC;
GRANT USAGE ON SCHEMA dashboard TO dashboard_reader;

REVOKE ALL ON dashboard.speakers_view FROM PUBLIC;
GRANT SELECT ON dashboard.speakers_view TO dashboard_reader;

REVOKE ALL ON dashboard.files_view FROM PUBLIC;
GRANT SELECT ON dashboard.files_view TO dashboard_reader;

REVOKE ALL ON dashboard.topics_view FROM PUBLIC;
GRANT SELECT ON dashboard.topics_view TO dashboard_reader;

REVOKE ALL ON dashboard.speeches_view FROM PUBLIC;
GRANT SELECT ON dashboard.speeches_view TO dashboard_reader;

-- 7. Give frontend role the dashboard_reader role (authenticated by default)
GRANT dashboard_reader TO authenticated;
-- If you want anonymous users to read, also grant to anon (uncomment the next line)
-- GRANT dashboard_reader TO anon;

-- 8. Optional: set restricted search_path for dashboard_owner
ALTER ROLE dashboard_owner SET search_path = dashboard, public;

-- 9. Validation / checks (read-only queries) to list current grants and ownership
-- 9a) Functions in dashboard schema with owners
SELECT
  n.nspname AS schema,
  p.proname AS function_name,
  pg_get_function_identity_arguments(p.oid) AS args,
  r.rolname AS owner
FROM pg_proc p
JOIN pg_namespace n ON p.pronamespace = n.oid
LEFT JOIN pg_roles r ON p.proowner = r.oid
WHERE n.nspname = 'dashboard'
  AND p.proname IN ('_fn_speakers_read','_fn_files_read','_fn_topics_read','_fn_speeches_read')
ORDER BY p.proname;

-- 9b) Function ACLs
SELECT
  n.nspname AS schema,
  p.proname AS function_name,
  pg_get_function_identity_arguments(p.oid) AS args,
  COALESCE(array_to_string(ARRAY(
    SELECT acl::text FROM unnest(coalesce(p.proacl, '{}')) AS acl
  ), E'\n'), '(no ACLs)') AS acl_array_text
FROM pg_proc p
JOIN pg_namespace n ON p.pronamespace = n.oid
WHERE n.nspname = 'dashboard'
  AND p.proname IN ('_fn_speakers_read','_fn_files_read','_fn_topics_read','_fn_speeches_read')
ORDER BY p.proname;

-- 9c) Views, their definitions and owner (owner from pg_class / pg_roles)
SELECT
  c.relname AS view_name,
  n.nspname AS schema,
  pg_get_viewdef(c.oid) AS view_definition,
  r.rolname AS owner
FROM pg_class c
JOIN pg_namespace n ON c.relnamespace = n.oid
LEFT JOIN pg_roles r ON c.relowner = r.oid
WHERE n.nspname = 'dashboard'
  AND c.relkind = 'v'
  AND c.relname IN ('speakers_view','files_view','topics_view','speeches_view');

-- 9d) View/table privileges from information_schema.table_privileges
SELECT grantee, table_schema, table_name, privilege_type
FROM information_schema.table_privileges
WHERE table_schema IN ('dashboard','private')
  AND table_name IN ('speakers_view','files_view','topics_view','speeches_view','speakers','files','topics','speeches')
ORDER BY table_schema, table_name, grantee, privilege_type;

-- 9e) Role membership for dashboard_owner/reader/authenticated
SELECT
  r.rolname AS role,
  r.rolsuper, r.rolinherit, r.rolcreaterole, r.rolcreatedb, r.rolcanlogin
FROM pg_roles r
WHERE r.rolname IN ('dashboard_owner','dashboard_reader','authenticated');

SELECT
  pg_get_userbyid(roleid) AS role,
  pg_get_userbyid(member) AS member
FROM pg_auth_members
WHERE roleid IN (SELECT oid FROM pg_roles WHERE rolname IN ('dashboard_owner','dashboard_reader'))
ORDER BY role, member;