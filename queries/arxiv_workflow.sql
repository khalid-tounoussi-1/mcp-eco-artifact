-- Purposefully selected historical case, not a defect in the probed implementation.
CREATE OR REPLACE TEMP VIEW arxiv_workflow_tools AS
SELECT s.repository_url AS server_url,
  t.server_id, t.tool_id, t.tool_name, t.original_description,
  t.input_json_schema, t.source, t.discovered_at
FROM mcp_servers s
JOIN mcp_tools t USING (server_id)
WHERE s.repository_url = 'https://github.com/blazickjp/arxiv-mcp-server'
  AND t.source = 'probe'
  AND t.tool_name IN ('search_papers', 'download_paper', 'read_paper');

CREATE OR REPLACE TEMP VIEW arxiv_workflow_issue AS
SELECT i.server_id, i.issue_id, i.source_url, i.title,
  i.body_text, i.state, i.created_at, i.closed_at
FROM mcp_servers s
JOIN ecosystem_issues i USING (server_id)
WHERE s.repository_url = 'https://github.com/blazickjp/arxiv-mcp-server'
  AND i.source_url = 'https://github.com/blazickjp/arxiv-mcp-server/issues/54';

-- Repeated issue details identify a shared repository-level case, not tool-version links.
SELECT t.tool_name, t.source, t.discovered_at,
  i.source_url, i.title, i.closed_at
FROM arxiv_workflow_tools t
JOIN arxiv_workflow_issue i USING (server_id)
ORDER BY t.tool_name;
