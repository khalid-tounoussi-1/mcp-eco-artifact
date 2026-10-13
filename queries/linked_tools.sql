-- Input views: mcp_servers, consumer_repos, repo_server_usage, mcp_tools.
-- Each view must read its corresponding Parquet file from the frozen release.
-- A link is a harvested declaration matched to a candidate server, not a call.
CREATE OR REPLACE TEMP VIEW linked_pairs AS
SELECT DISTINCT u.repo_id, u.server_id
FROM repo_server_usage AS u
JOIN consumer_repos AS c ON c.repo_id = u.repo_id
JOIN mcp_servers AS s ON s.server_id = u.server_id
WHERE u.repo_id IS NOT NULL AND u.server_id IS NOT NULL;

-- Keep individual tool observations and their origin. Do not merge the sources.
CREATE OR REPLACE TEMP VIEW linked_tool_observations AS
SELECT p.repo_id, c.repository_url AS consumer_url,
       p.server_id, s.repository_url AS server_url, s.server_name,
       t.tool_id, t.tool_name, t.original_description, t.input_json_schema, t.source
FROM linked_pairs AS p
JOIN consumer_repos AS c ON c.repo_id = p.repo_id
JOIN mcp_servers AS s ON s.server_id = p.server_id
JOIN mcp_tools AS t ON t.server_id = p.server_id
WHERE t.tool_name IS NOT NULL AND TRIM(t.tool_name) <> '';

-- Search the names and descriptions of tools whose server has at least one
-- linked consuming repository. A search match is a text match, not a
-- classification of what the tool does.
--
-- One row per tool observation. A tool reported by both sources appears twice,
-- once per source. Linked repositories are counted per server before the join,
-- so tools and repositories are never multiplied. The setup example is the
-- first linked declaration by consumer URL, file path, and usage_id.
CREATE OR REPLACE TEMP MACRO search_linked_tools(term) AS TABLE
WITH per_server AS (
  SELECT server_id, COUNT(DISTINCT repo_id) AS linked_repositories
  FROM linked_pairs
  GROUP BY server_id
),
example AS (
  SELECT u.server_id,
         c.repository_url AS example_consumer_url,
         u.config_file_path AS example_config_file_path,
         u.match_method AS example_match_method
  FROM repo_server_usage AS u
  JOIN consumer_repos AS c ON c.repo_id = u.repo_id
  WHERE u.server_id IS NOT NULL
  QUALIFY row_number() OVER (
    PARTITION BY u.server_id
    ORDER BY c.repository_url, u.config_file_path, u.usage_id) = 1
)
SELECT t.tool_id, t.tool_name, t.source,
       t.server_id, s.repository_url AS server_url, s.server_name,
       p.linked_repositories,
       e.example_consumer_url, e.example_config_file_path, e.example_match_method,
       t.input_json_schema
FROM mcp_tools AS t
JOIN per_server AS p ON p.server_id = t.server_id
JOIN mcp_servers AS s ON s.server_id = t.server_id
JOIN example AS e ON e.server_id = t.server_id
WHERE t.tool_name IS NOT NULL AND TRIM(t.tool_name) <> ''
  AND (contains(lower(t.tool_name), lower(term))
       OR contains(lower(replace(t.tool_name, '_', ' ')), lower(term))
       OR contains(lower(COALESCE(t.original_description, '')), lower(term)));
