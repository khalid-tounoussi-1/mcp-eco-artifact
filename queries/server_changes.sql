-- Input views: server_pull_requests, client_pull_requests, pr_reviews.
-- Uses pr_key from queries/macros.sql.
--
-- Search one server's pull request titles and bodies for a term, such as a tool
-- name or an input field. A text match is not a classification of what the
-- pull request changed.
--
-- One row per pull request, identified by pr_key. The release can store one
-- pull request more than once: under two pr_id values, under two spellings of
-- its URL, under two candidate servers, or in both pull request tables. All
-- stored rows with the same pr_key, in either table, are gathered here. Every
-- distinct spelling, non-null state, and merge time is listed. An empty
-- merged_at_values list means no stored row has a merge time.
--
-- Reviews reference pr_id without a declared foreign key. Reviews are gathered
-- over every pr_id of the pull request, counted by distinct review_id, and only
-- when none of those pr_id values belongs to another pull request in either
-- table. Otherwise the review columns are NULL. They are also NULL when no
-- review row exists: the release cannot tell "no review" from "not harvested".
CREATE OR REPLACE TEMP MACRO server_pr_search(sid, term) AS TABLE
WITH hits AS (
  SELECT DISTINCT pr_key(pr_url) AS pr_key
  FROM server_pull_requests
  WHERE server_id = sid
    AND (contains(lower(title), lower(term))
         OR contains(lower(COALESCE(body_text, '')), lower(term)))
),
stored AS (
  SELECT 'server' AS stored_in, s.pr_id, s.pr_url, h.pr_key, s.title, s.body_text, s.state, s.created_at, s.merged_at
  FROM server_pull_requests AS s JOIN hits AS h ON pr_key(s.pr_url) = h.pr_key
  UNION ALL
  SELECT 'client', c.pr_id, c.pr_url, h.pr_key, c.title, c.body_text, c.state, c.created_at, c.merged_at
  FROM client_pull_requests AS c JOIN hits AS h ON pr_key(c.pr_url) = h.pr_key
),
flagged AS (
  SELECT x.*,
         EXISTS (SELECT 1 FROM server_pull_requests AS s
                 WHERE s.pr_id = x.pr_id AND pr_key(s.pr_url) <> x.pr_key)
      OR EXISTS (SELECT 1 FROM client_pull_requests AS c
                 WHERE c.pr_id = x.pr_id AND pr_key(c.pr_url) <> x.pr_key) AS pr_id_reused
  FROM stored AS x
),
per_pr AS (
  SELECT pr_key,
         list_sort(list_distinct(list(pr_url))) AS pr_urls,
         arg_min(title, pr_id) AS title,
         list_sort(list_distinct(list(pr_id))) AS pr_ids,
         COUNT(*) FILTER (WHERE stored_in = 'server') AS server_rows,
         COUNT(*) FILTER (WHERE stored_in = 'client') AS client_rows,
         list_sort(list_distinct(list(state))) AS states,
         MIN(created_at) AS created_at,
         list_sort(list_distinct(list(merged_at))) AS merged_at_values,  -- list_distinct drops NULLs
         bool_or(contains(lower(title), lower(term))) AS term_in_title,
         bool_or(contains(lower(COALESCE(body_text, '')), lower(term))) AS term_in_body,
         NOT bool_or(pr_id_reused) AS review_attribution_clean
  FROM flagged
  GROUP BY pr_key
),
review_counts AS (
  SELECT ids.pr_key,
         COUNT(DISTINCT v.review_id) AS review_rows,
         COUNT(DISTINCT v.review_id) FILTER (WHERE v.review_state = 'APPROVED') AS approved_review_rows
  FROM (SELECT DISTINCT pr_key, pr_id FROM stored) AS ids
  JOIN pr_reviews AS v ON v.pr_id = ids.pr_id
  GROUP BY ids.pr_key
)
SELECT p.*,
       CASE WHEN p.review_attribution_clean THEN r.review_rows END AS review_rows,
       CASE WHEN p.review_attribution_clean THEN r.approved_review_rows END AS approved_review_rows
FROM per_pr AS p
LEFT JOIN review_counts AS r ON r.pr_key = p.pr_key;
