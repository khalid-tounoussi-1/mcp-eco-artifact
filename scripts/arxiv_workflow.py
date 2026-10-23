"""Researcher example: arXiv tools and a historical tool-coordination report.

The issue was closed before the probe observations. The shared server_id
establishes repository identity, not a common implementation version or defect.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from checks import one, require, text_sha256
from common import (DEFAULT_DATA_DIR, connect, fetch, load_release, output_path,
                    plain, run, run_sql_file, write_json)
from workflow_checks import check_schemas, expected_case


def reproduce(con, expected: dict) -> dict:
    run_sql_file(con, "arxiv_workflow.sql")
    rows = fetch(con, "SELECT * FROM arxiv_workflow_tools ORDER BY tool_name")
    tools = check_schemas(rows, expected["tools"])
    require(all(str(r["server_id"]) == expected["server_id"] for r in rows), "Wrong capability candidate")
    issue = one(fetch(con, "SELECT * FROM arxiv_workflow_issue"), "historical arXiv issue")
    require(str(issue["server_id"]) == expected["server_id"], "Issue belongs to another candidate")
    require(issue["issue_id"] == expected["issue_id"], "Wrong issue identity")
    require(text_sha256(issue["body_text"]) == expected["body_sha256"], "Changed stored issue body")
    require(all(term in issue["body_text"] for term in ("download_paper", "read_paper", "asynchronous")),
            "Issue does not support the selected coordination question")
    require(issue["closed_at"] is not None and
            all(issue["closed_at"] < r["discovered_at"] for r in rows),
            "Historical issue is not closed before the selected probe observations")
    for tool, row in zip(tools, rows):
        tool["description"] = row["original_description"]
        tool["observed_at"] = row["discovered_at"]
    return {"server_url": expected["server_url"], "tools": tools, "issue": issue}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    release = load_release()
    output = output_path(args.output, "arxiv-workflow.json", args.data_dir)
    con, hashes = connect(release, args.data_dir, "arxiv")
    case = reproduce(con, expected_case(release, "arxiv"))
    write_json(output, plain({"release_revision": release.revision, "input_sha256": hashes,
                             "selection": "Purposefully selected illustrative case", "case": case,
                             "bounds": "Historical issue report linked at repository level. The issue "
                             "closed before the probes and is not tied to their implementation version. "
                             "No MCP execution, reproduced failure, or current-defect claim."}))
    for tool in case["tools"]:
        print(f"{tool['tool_name']} [probe]: required inputs {tool['input_json_schema']['required']}")
    print(f"Historical issue: {case['issue']['source_url']}")
    print(f"Closed: {case['issue']['closed_at']}. Probe dates are recorded separately in the output.")
    print("PASS: selected probe schemas, repository linkage, issue identity, and historical timing")
    print(f"Wrote {output}")


if __name__ == "__main__":
    run(main)
