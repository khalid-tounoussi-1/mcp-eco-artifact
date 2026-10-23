"""New workflow selections and checks on synthetic records, without network access."""
from __future__ import annotations

import json
from datetime import datetime

import duckdb
import pytest

from arxiv_workflow import reproduce
from checks import CheckFailed, text_sha256
from common import QUERIES_DIR, fetch
from workflow_checks import check_schemas

SCHEMA = {"type": "object", "required": ["query"],
          "properties": {"query": {"type": "string"}}}


def test_github_query_keeps_probes_and_package_matches_without_transport_fanout():
    con = duckdb.connect()
    con.execute("CREATE TABLE mcp_server_transports(server_id VARCHAR, package_identifier VARCHAR)")
    con.executemany("INSERT INTO mcp_server_transports VALUES (?, ?)",
                    [("S1", "@modelcontextprotocol/server-github")] * 2)
    con.execute("CREATE TABLE mcp_tools(server_id VARCHAR, tool_name VARCHAR, input_json_schema VARCHAR, source VARCHAR)")
    names = ["get_issue", "get_file_contents", "create_pull_request"]
    con.executemany("INSERT INTO mcp_tools VALUES (?, ?, ?, ?)",
                    [("S1", n, json.dumps(SCHEMA), source) for n in names for source in ("probe", "glama")])
    con.execute("CREATE TABLE consumer_repos(repo_id INTEGER, repository_url VARCHAR)")
    con.executemany("INSERT INTO consumer_repos VALUES (?, ?)",
                    [(1, "https://github.com/redis/RedisInsight"), (2, "https://github.com/synthetic/other")])
    con.execute("""CREATE TABLE repo_server_usage(server_id VARCHAR, repo_id INTEGER,
                   config_file_path VARCHAR, raw_command VARCHAR, raw_args VARCHAR, match_method VARCHAR)""")
    con.executemany("INSERT INTO repo_server_usage VALUES (?, ?, ?, ?, ?, ?)", [
        ("S1", 1, "mcp.json", "npx", "[]", "package_ver"),
        ("S1", 1, "mcp.json", "npx", "[]", "v1"),
        ("S1", 1, ".cursor/mcp.json", "npx", "[]", "package"),
        ("S1", 2, "mcp.json", "npx", "[]", "package"),
    ])
    rows = fetch(con, (QUERIES_DIR / "github_workflow.sql").read_text())
    assert sorted(r["tool_name"] for r in rows) == sorted(names)
    assert all(r["config_file_path"] == "mcp.json" and r["match_method"] == "package_ver" for r in rows)


def test_schema_checks_reject_duplicate_observations_and_changed_sources():
    spec = [{"tool_id": "T1", "tool_name": "synthetic", "schema": SCHEMA,
             "example_input": {"query": "example"}}]
    row = {"tool_id": "T1", "tool_name": "synthetic",
           "input_json_schema": json.dumps(SCHEMA), "source": "probe"}
    assert check_schemas([row], spec)[0]["source"] == "probe"
    with pytest.raises(CheckFailed, match="duplicated"):
        check_schemas([row, row], spec)
    with pytest.raises(CheckFailed, match="not a probe"):
        check_schemas([dict(row, source="glama")], spec)


@pytest.fixture
def arxiv_case():
    con = duckdb.connect()
    con.execute("CREATE TABLE mcp_servers(server_id VARCHAR, repository_url VARCHAR)")
    con.execute("INSERT INTO mcp_servers VALUES ('S1', 'https://github.com/blazickjp/arxiv-mcp-server')")
    con.execute("""CREATE TABLE mcp_tools(server_id VARCHAR, tool_id VARCHAR, tool_name VARCHAR,
                   original_description VARCHAR, input_json_schema VARCHAR, source VARCHAR, discovered_at TIMESTAMP)""")
    names = ["search_papers", "download_paper", "read_paper"]
    for name in names:
        con.execute("INSERT INTO mcp_tools VALUES (?, ?, ?, ?, ?, ?, ?)",
                    ["S1", name, name, "Synthetic description", json.dumps(SCHEMA), "probe", datetime(2026, 5, 24)])
    con.execute("""CREATE TABLE ecosystem_issues(server_id VARCHAR, issue_id BIGINT, source_url VARCHAR,
                   title VARCHAR, body_text VARCHAR, state VARCHAR, created_at TIMESTAMP, closed_at TIMESTAMP)""")
    body = "Synthetic report: download_paper read_paper asynchronous"
    con.execute("INSERT INTO ecosystem_issues VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                ["S1", 54, "https://github.com/blazickjp/arxiv-mcp-server/issues/54", "Synthetic issue",
                 body, "closed", datetime(2025, 12, 15), datetime(2026, 4, 26)])
    expected = {"server_id": "S1", "server_url": "https://github.com/blazickjp/arxiv-mcp-server",
                "issue_id": 54, "body_sha256": text_sha256(body),
                "tools": [{"tool_id": name, "tool_name": name, "schema": SCHEMA,
                           "example_input": {"query": "example"}} for name in names]}
    return con, expected


def test_arxiv_case_keeps_one_historical_report_separate_from_tools(arxiv_case):
    con, expected = arxiv_case
    result = reproduce(con, expected)
    assert result["issue"]["issue_id"] == 54
    assert {t["tool_name"] for t in result["tools"]} == {t["tool_name"] for t in expected["tools"]}
    assert result["issue"]["closed_at"] < min(t["observed_at"] for t in result["tools"])


def test_arxiv_case_rejects_a_changed_report(arxiv_case):
    con, expected = arxiv_case
    con.execute("UPDATE ecosystem_issues SET body_text = 'Unrelated synthetic text'")
    with pytest.raises(CheckFailed, match="Changed stored issue body"):
        reproduce(con, expected)


def test_arxiv_case_rejects_an_issue_closed_after_the_probes(arxiv_case):
    con, expected = arxiv_case
    con.execute("UPDATE ecosystem_issues SET closed_at = TIMESTAMP '2026-06-01'")
    with pytest.raises(CheckFailed, match="closed before"):
        reproduce(con, expected)
