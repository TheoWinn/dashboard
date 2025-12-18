SET ROLE authenticated;
SELECT COUNT(*) AS speakers_view_count FROM dashboard.speakers_view;
RESET ROLE;

SET ROLE authenticated;
SELECT * FROM dashboard_internal._fn_speakers_read() LIMIT 1;
RESET ROLE;

SET ROLE authenticated;
SELECT COUNT(*) AS private_speakers_count FROM private.speakers;
RESET ROLE;

SET ROLE anon;
SELECT COUNT(*) AS files_view_count FROM dashboard.files_view;
RESET ROLE;

SET ROLE anon;
SELECT * FROM dashboard_internal._fn_files_read() LIMIT 1;
RESET ROLE;

SET ROLE dashboard_owner;
SELECT * FROM dashboard_internal._fn_topics_read() LIMIT 3;
RESET ROLE;

SET ROLE dashboard_owner;
SELECT COUNT(*) AS private_speeches_count FROM private.speeches;
RESET ROLE;

SET ROLE dashboard_owner;
SELECT * FROM dashboard.speeches_view LIMIT 2;
RESET ROLE;

SET ROLE authenticated;
SET LOCAL search_path = dashboard_internal, public;
-- attempt to call by unqualified name
SELECT * FROM _fn_speakers_read() LIMIT 1;
RESET ROLE;

CREATE OR REPLACE FUNCTION public._fn_speakers_read()
RETURNS TABLE (speaker_id bigint)
LANGUAGE sql
AS $$
  SELECT 999::bigint;
$$;

SET ROLE authenticated;
SELECT * FROM dashboard.speakers_view LIMIT 1;
RESET ROLE;

DROP FUNCTION IF EXISTS public._fn_speakers_read();

SELECT n.nspname AS schema,
       p.proname AS function_name,
       pg_get_function_identity_arguments(p.oid) AS args,
       COALESCE(array_to_string(ARRAY(
         SELECT acl::text FROM unnest(coalesce(p.proacl, '{}')) AS acl
       ), E'\n'), '(no ACLs)') AS acl
FROM pg_proc p
JOIN pg_namespace n ON p.pronamespace = n.oid
WHERE n.nspname = 'dashboard_internal'
  AND p.proname IN ('_fn_speakers_read','_fn_files_read','_fn_topics_read','_fn_speeches_read')
ORDER BY p.proname;

SELECT c.relname AS view_name,
       n.nspname AS schema,
       pg_get_viewdef(c.oid) AS view_definition,
       r.rolname AS owner
FROM pg_class c
JOIN pg_namespace n ON c.relnamespace = n.oid
LEFT JOIN pg_roles r ON c.relowner = r.oid
WHERE n.nspname = 'dashboard'
  AND c.relkind = 'v'
  AND c.relname IN ('speakers_view','files_view','topics_view','speeches_view');


SELECT grantee, table_schema, table_name, privilege_type
FROM information_schema.table_privileges
WHERE table_schema IN ('dashboard','dashboard_internal','private')
  AND table_name IN ('speakers_view','files_view','topics_view','speeches_view','speakers','files','topics','speeches')
ORDER BY table_schema, table_name, grantee, privilege_type;

SELECT nspname,
       has_schema_privilege('authenticated', nspname, 'USAGE') AS authenticated_has_usage,
       has_schema_privilege('anon', nspname, 'USAGE') AS anon_has_usage
FROM pg_namespace
WHERE nspname IN ('dashboard','dashboard_internal','private');