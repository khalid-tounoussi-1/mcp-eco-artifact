-- Selected reference GitHub package and RedisInsight setup, from the frozen release.
-- One row per selected probe tool paired with the same configuration declaration.
SELECT t.tool_name, t.input_json_schema,
  c.repository_url, u.config_file_path,
  u.raw_command, u.raw_args, u.match_method
FROM mcp_tools t
JOIN repo_server_usage u USING (server_id)
JOIN consumer_repos c USING (repo_id)
WHERE t.server_id IN (
  SELECT server_id FROM mcp_server_transports
  WHERE package_identifier =
    '@modelcontextprotocol/server-github')
  AND t.source = 'probe'
  AND t.tool_name IN ('get_issue',
    'get_file_contents', 'create_pull_request')
  AND u.match_method IN ('package', 'package_ver')
  AND lower(c.repository_url) =
    'https://github.com/redis/redisinsight'
  AND u.config_file_path = 'mcp.json'
ORDER BY t.tool_name;
