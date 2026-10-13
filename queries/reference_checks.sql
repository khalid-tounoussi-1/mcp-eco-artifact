-- Optional extension of the paper listing, as in the dataset card's pandas example.
-- Input views: repo_server_usage, mcp_servers, consumer_repos.
-- Foreign keys are declared in schema.sql but Parquet does not enforce them, so
-- count resolved pairs whose repository or server record is absent.
WITH pairs AS (
  SELECT DISTINCT repo_id, server_id
  FROM repo_server_usage
  WHERE server_id IS NOT NULL
    AND repo_id IS NOT NULL)
SELECT
  COUNT(*) AS resolved_pairs,
  COUNT(*) FILTER (WHERE NOT EXISTS (
    SELECT 1 FROM consumer_repos AS c WHERE c.repo_id = p.repo_id)) AS pairs_without_consumer_record,
  COUNT(*) FILTER (WHERE NOT EXISTS (
    SELECT 1 FROM mcp_servers AS s WHERE s.server_id = p.server_id)) AS pairs_without_server_record
FROM pairs AS p
