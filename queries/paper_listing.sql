-- Listing 1 of the paper: distinct configured repositories per candidate server.
-- Input views: repo_server_usage, mcp_servers, each reading its pinned Parquet file.
--
-- Same steps as the paper: drop declarations without a matched server, reduce
-- declarations to distinct repository/server pairs, join server names, count
-- distinct repositories. The only change is the tie-break on server_id, which
-- makes the row order stable. It does not change any key or count.
--
-- configured_repositories counts consuming repositories with at least one
-- harvested configuration declaration matched to the server. It is not an
-- installation count, an active-user count, or a measure of runtime use.
WITH pairs AS (
  SELECT DISTINCT repo_id, server_id
  FROM repo_server_usage
  WHERE server_id IS NOT NULL
    AND repo_id IS NOT NULL)
SELECT s.server_id, s.server_name,
  COUNT(DISTINCT p.repo_id)
    AS configured_repositories
FROM pairs AS p
JOIN mcp_servers AS s
  ON s.server_id = p.server_id
GROUP BY s.server_id, s.server_name
ORDER BY configured_repositories DESC, s.server_id
