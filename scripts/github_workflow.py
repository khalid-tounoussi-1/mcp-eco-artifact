"""Engineer example: inspect reference GitHub tools and RedisInsight's setup.

The example reads stored probe schemas and a package-matched declaration.
It does not run a tool, create a pull request, or establish version compatibility.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from checks import one, require
from common import (DEFAULT_DATA_DIR, QUERIES_DIR, connect, fetch, load_release,
                    output_path, plain, run, write_json)
from workflow_checks import check_schemas, expected_case


def reproduce(con, expected: dict) -> dict:
    package = one(fetch(con, """SELECT DISTINCT server_id FROM mcp_server_transports
                                WHERE package_identifier = ?""",
                        [expected["package_identifier"]]), "reference GitHub package mapping")
    require(str(package["server_id"]) == expected["server_id"], "Reference package maps to another candidate")
    rows = fetch(con, (QUERIES_DIR / "github_workflow.sql").read_text())
    tools = check_schemas(rows, expected["tools"])
    for row in rows:
        require(row["repository_url"].lower() == expected["consumer_url"].lower(), "Wrong consuming project")
        setup = {k: row[k] for k in ("config_file_path", "raw_command", "match_method")}
        setup["raw_args"] = json.loads(row["raw_args"])
        require(setup == expected["setup"], "Changed configuration declaration")
    return {"server_id": str(package["server_id"]),
            "package_identifier": expected["package_identifier"], "tools": tools,
            "consumer_url": expected["consumer_url"], "setup": expected["setup"]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    release = load_release()
    output = output_path(args.output, "github-workflow.json", args.data_dir)
    con, hashes = connect(release, args.data_dir, "github")
    case = reproduce(con, expected_case(release, "github"))
    write_json(output, plain({"release_revision": release.revision, "input_sha256": hashes,
                             "selection": "Purposefully selected illustrative case", "case": case,
                             "bounds": "Older reference package, not github/github-mcp-server. "
                             "Stored schemas and a configuration declaration, not runtime use or "
                             "version-specific compatibility. No MCP tool was invoked."}))
    for tool in case["tools"]:
        print(f"{tool['tool_name']} [probe]: required inputs {tool['input_json_schema']['required']}")
    print(f"Setup: {case['consumer_url']} / {case['setup']['config_file_path']}")
    print("PASS: selected probe schemas, package mapping, and configuration declaration")
    print(f"Wrote {output}")


if __name__ == "__main__":
    run(main)
