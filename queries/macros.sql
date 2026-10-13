-- Shared DuckDB macros. scripts/common.py loads this file after creating the
-- table views, so every script and scripts/run_query.py can use them. Run it
-- first when you use the queries in another DuckDB session.
--
-- pr_key: a pull request key built from a stored URL, shared by all spellings
-- of that URL.
-- The release spells some URLs in two ways. Owner and repository names can
-- differ in letter case, which GitHub ignores. Some URLs carry the
-- /tree/<ref>/<dir> segment of a monorepo candidate before /pull/N, which is
-- not a GitHub URL. pr_key folds case and drops that segment, so
--   https://github.com/Owner/Repo/tree/main/pkg/pull/7
--   https://github.com/owner/repo/pull/7
-- get the same key. Only the segment right after owner/repo is dropped, and
-- only for github.com URLs. Other URLs are returned unchanged. A pull request
-- of a renamed repository can still appear under both names. pr_key does not
-- detect renames.
CREATE OR REPLACE TEMP MACRO pr_key(url) AS
  CASE WHEN starts_with(lower(url), 'https://github.com/')
       THEN regexp_replace(lower(url), '^(https://github\.com/[^/]+/[^/]+)/tree/.*/pull/', '\1/pull/')
       ELSE url
  END;
