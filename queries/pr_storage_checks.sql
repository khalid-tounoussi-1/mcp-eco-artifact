-- Input views: server_pull_requests, client_pull_requests, pr_reviews, and
-- mcp_servers. Uses pr_key from queries/macros.sql.
--
-- How often one pull request is stored more than once. A pull request is one
-- pr_key. Each column names its unit: stored rows, exact URLs, pull requests,
-- pr_id values, reviews, or row groups. docs/data-dictionary.md reports these
-- numbers.
WITH stored AS (
  SELECT 'server' AS stored_in, pr_id, pr_url, pr_key(pr_url) AS pr_key, server_id, title, created_at
  FROM server_pull_requests
  UNION ALL
  SELECT 'client', pr_id, pr_url, pr_key(pr_url), NULL, title, created_at
  FROM client_pull_requests
),
verbatim_twins AS (
  SELECT pr_url, COUNT(*) AS n, min(server_id) AS server_a, max(server_id) AS server_b
  FROM server_pull_requests
  GROUP BY pr_url
  HAVING COUNT(*) > 1
),
twin_servers AS (
  SELECT t.pr_url,
         starts_with(lower(b.repository_url), lower(a.repository_url) || '/')
           OR starts_with(lower(a.repository_url), lower(b.repository_url) || '/') AS subdirectory
  FROM verbatim_twins AS t
  JOIN mcp_servers AS a ON a.server_id = t.server_a
  JOIN mcp_servers AS b ON b.server_id = t.server_b
  WHERE t.server_a <> t.server_b
),
server_spellings AS (
  SELECT pr_key, bool_or(pr_url LIKE '%/tree/%/pull/%') AS tree_segment
  FROM stored
  WHERE stored_in = 'server'
  GROUP BY pr_key
  HAVING COUNT(DISTINCT pr_url) > 1
),
multi_id AS (
  SELECT pr_key, COUNT(DISTINCT pr_id) AS ids FROM stored GROUP BY pr_key HAVING COUNT(DISTINCT pr_id) > 1
),
reviewed AS (
  SELECT m.pr_key, COUNT(DISTINCT s.pr_id) FILTER (WHERE r.pr_id IS NOT NULL) AS ids_with_reviews
  FROM multi_id AS m
  JOIN stored AS s USING (pr_key)
  LEFT JOIN (SELECT DISTINCT pr_id FROM pr_reviews) AS r ON r.pr_id = s.pr_id
  GROUP BY m.pr_key
),
shared_ids AS (
  SELECT s.pr_id, s.pr_key = c.pr_key AS same_pull_request
  FROM stored AS s JOIN stored AS c ON c.pr_id = s.pr_id
  WHERE s.stored_in = 'server' AND c.stored_in = 'client'
),
-- Rows that share pull request number, title, and creation time under
-- different repository names suggest a renamed repository. pr_key keeps them
-- apart.
keyed AS (
  SELECT *,
         regexp_extract(pr_key, '/pull/([0-9]+)$', 1) AS number,
         regexp_extract(pr_key, '^https://github\.com/([^/]+/[^/]+)/pull/', 1) AS repository
  FROM stored
  WHERE created_at IS NOT NULL
),
rename_groups AS (
  SELECT number, title, created_at, list_sort(list_distinct(list(repository))) AS repositories
  FROM keyed
  GROUP BY number, title, created_at
  HAVING COUNT(DISTINCT repository) > 1
),
rename_keys AS (
  SELECT g.number, g.title, g.created_at, k.pr_key, COUNT(DISTINCT r.review_id) AS reviews
  FROM rename_groups AS g
  JOIN (SELECT DISTINCT number, title, created_at, pr_key, pr_id FROM keyed) AS k
    USING (number, title, created_at)
  LEFT JOIN pr_reviews AS r ON r.pr_id = k.pr_id
  GROUP BY g.number, g.title, g.created_at, k.pr_key
)
SELECT
  (SELECT COUNT(*) FROM server_pull_requests) AS server_rows,
  (SELECT COUNT(DISTINCT pr_url) FROM server_pull_requests) AS server_distinct_exact_urls,
  (SELECT COUNT(DISTINCT pr_key) FROM stored WHERE stored_in = 'server') AS server_pull_requests,
  (SELECT COUNT(*) FROM verbatim_twins) AS server_urls_stored_twice_verbatim,
  (SELECT SUM(n) FROM verbatim_twins) AS server_rows_of_those_urls,
  (SELECT COUNT(*) FROM twin_servers) AS of_those_urls_under_two_servers,
  (SELECT COUNT(*) FILTER (WHERE subdirectory) FROM twin_servers) AS of_which_repository_and_subdirectory,
  (SELECT COUNT(*) FILTER (WHERE NOT subdirectory) FROM twin_servers) AS of_which_differently_named_repositories,
  (SELECT COUNT(*) FROM server_spellings) AS server_pull_requests_with_several_url_spellings,
  (SELECT COUNT(*) FILTER (WHERE NOT tree_segment) FROM server_spellings) AS of_which_letter_case_only,
  (SELECT COUNT(*) FILTER (WHERE tree_segment) FROM server_spellings) AS of_which_tree_segment,
  (SELECT COUNT(*) FROM server_pull_requests WHERE pr_url LIKE '%/tree/%/pull/%') AS server_rows_with_tree_segment_url,
  (SELECT COUNT(*) FROM server_pull_requests AS p JOIN mcp_servers AS m USING (server_id)
    WHERE p.pr_url LIKE '%/tree/%/pull/%'
      AND starts_with(p.pr_url, m.repository_url || '/pull/')) AS of_which_server_url_plus_pull_number,
  (SELECT COUNT(*) FROM multi_id) AS pull_requests_with_several_pr_ids_both_tables,
  (SELECT MAX(ids) FROM multi_id) AS max_pr_ids_per_pull_request,
  (SELECT COUNT(*) FILTER (WHERE ids_with_reviews = 1) FROM reviewed) AS of_those_reviews_under_one_pr_id,
  (SELECT COUNT(*) FILTER (WHERE ids_with_reviews > 1) FROM reviewed) AS of_those_reviews_under_several_pr_ids,
  (SELECT COUNT(*) FROM shared_ids) AS pr_id_values_in_both_tables,
  (SELECT COUNT(*) FILTER (WHERE same_pull_request) FROM shared_ids) AS of_which_same_pull_request,
  (SELECT COUNT(*) FILTER (WHERE NOT same_pull_request) FROM shared_ids) AS of_which_different_pull_requests,
  -- the same review (reviewer, time, state, text) under two ids of one pull request
  (SELECT COUNT(*) FROM (
     SELECT s.pr_key, r.reviewer_login, r.submitted_at, r.review_state, md5(COALESCE(r.feedback_text, ''))
     FROM pr_reviews AS r JOIN stored AS s ON s.pr_id = r.pr_id
     GROUP BY ALL
     HAVING COUNT(DISTINCT r.pr_id) > 1)) AS reviews_repeated_under_several_pr_ids,
  -- creation-time spread among the rows that share one pr_key
  (SELECT MAX(epoch(mx) - epoch(mn)) FROM (
     SELECT MIN(created_at) AS mn, MAX(created_at) AS mx
     FROM stored GROUP BY pr_key HAVING COUNT(*) > 1)) AS max_created_at_spread_seconds_within_one_key,
  (SELECT COUNT(*) FROM rename_groups) AS row_groups_under_several_repository_names,
  (SELECT COUNT(DISTINCT repositories) FROM rename_groups) AS of_those_repository_name_sets,
  (SELECT COUNT(DISTINCT pr_key) FROM rename_keys) AS pull_requests_in_those_groups,
  (SELECT COUNT(DISTINCT pr_key) FROM rename_keys AS a
    WHERE a.reviews = 0
      AND EXISTS (SELECT 1 FROM rename_keys AS b
                  WHERE (b.number, b.title, b.created_at) = (a.number, a.title, a.created_at)
                    AND b.pr_key <> a.pr_key AND b.reviews > 0)) AS of_which_no_reviews_while_a_renamed_twin_has_some
