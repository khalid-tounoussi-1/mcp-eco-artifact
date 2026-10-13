"""Software-engineer story: from a needed tool to a project setup example.

Part 1 searches stored tool names and descriptions for --term, among servers
with at least one linked consuming repository. It works for any term.

Part 2 checks the case used in the paper: Glama's report of Exa's
web_search_exa tool and the .mcp.json declaration in the gap project. That case
was selected deliberately for the paper. It is an assertion target, not the
top search result and not a sample.

Nothing here runs an MCP server or executes a command found in a record.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from checks import (
    one,
    observations_by_source,
    require,
    required_inputs,
    text_sha256,
    validate_examples,
)
from common import (
    DEFAULT_DATA_DIR,
    EVIDENCE_DIR,
    connect,
    fetch,
    load_release,
    output_path,
    plain,
    run,
    run_sql_file,
    write_json,
)

SEARCH_SQL = """
SELECT * FROM search_linked_tools(?)
ORDER BY linked_repositories DESC, tool_name, source, server_id
"""


def search(con, term: str) -> list[dict]:
    rows = fetch(con, SEARCH_SQL, [term])
    for r in rows:
        r["required_inputs"] = required_inputs(r.pop("input_json_schema"))
    return plain(rows)


def selected_case(con, expected: dict) -> dict:
    """Port of the checks behind the paper's engineer story."""
    tool = one(
        fetch(
            con,
            """SELECT * FROM linked_tool_observations
               WHERE server_url = ? AND consumer_url = ? AND tool_name = ? AND source = ?""",
            [
                expected["tool"]["server_url"],
                expected["tool"]["consumer_url"],
                expected["tool"]["tool_name"],
                expected["tool"]["source"],
            ],
        ),
        "selected tool link",
    )
    for key in ("tool_id", "server_id"):
        require(str(tool[key]) == expected["tool"][key], f"selected {key} differs from the expected record")

    schema_text = tool["input_json_schema"]
    require(text_sha256(schema_text) == expected["input_json_schema_sha256"], "stored input schema differs")
    schema = json.loads(schema_text)
    require(schema["properties"]["query"]["type"] == "string", "query must be a string")
    require("query" in schema["required"], "query must be required")
    require("livecrawl" in schema["properties"], "stored schema must contain livecrawl")
    require(schema["required"] == expected["stored_schema_required"], "required inputs differ")
    require(sorted(schema["properties"]) == expected["stored_schema_fields"], "schema fields differ")
    examples = expected["schema_examples"]
    validate_examples(schema_text, examples["valid"], examples["invalid"])

    setup = one(
        fetch(
            con,
            """SELECT usage_id, config_file_path, raw_command, raw_args, match_method
               FROM repo_server_usage
               WHERE repo_id = ? AND server_id = ? AND config_file_path = ?""",
            [tool["repo_id"], tool["server_id"], expected["setup"]["config_file_path"]],
        ),
        "setup declaration",
    )
    setup = plain(setup)
    require(setup == expected["setup"], "setup declaration differs from the expected record")
    require(setup["raw_command"] == "npx", "unexpected launcher")
    require(expected["package_identifier"] in json.loads(setup["raw_args"]), "missing package argument")

    package = one(
        fetch(
            con,
            "SELECT DISTINCT server_id FROM mcp_server_transports WHERE package_identifier = ?",
            [expected["package_identifier"]],
        ),
        "package mapping",
    )
    require(package["server_id"] == tool["server_id"], "package maps to another server")

    return {
        "tool": plain({k: tool[k] for k in ("tool_id", "tool_name", "source", "server_id", "server_url", "consumer_url")}),
        "required_inputs": schema["required"],
        "input_fields": sorted(schema["properties"]),
        "schema_examples": examples,
        "setup": setup,
        "package_identifier": expected["package_identifier"],
        "package_maps_to_one_server": True,
        "tool_observations_by_source": observations_by_source(con, tool["server_id"]),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR, help="default: <repository>/data")
    parser.add_argument("--output", type=Path, help="JSON path, default: <repository>/outputs/engineer.json")
    parser.add_argument("--term", default="web search", help="text to find in tool names or descriptions")
    parser.add_argument("--limit", type=int, default=10, help="search results to print")
    args = parser.parse_args()

    expected = json.loads((EVIDENCE_DIR / "exa-expected.json").read_text())["engineer"]
    release = load_release()
    output = output_path(args.output, "engineer.json", args.data_dir)
    con, hashes = connect(release, args.data_dir, "engineer")
    run_sql_file(con, "linked_tools.sql")

    matches = search(con, args.term)
    servers = {m["server_id"] for m in matches}
    print(f"Part 1. Search for {args.term!r} in tool names and descriptions")
    print(f"{len(matches)} tool observations on {len(servers)} servers with a linked consuming repository.")
    print("One row per tool observation and source. 'linked' counts consuming repositories per server.")
    if not matches:
        print("  No match. Try a shorter or different term.")
    for m in matches[: args.limit]:
        print(
            f"  {m['tool_name']} [{m['source']}]  required={m['required_inputs']}  "
            f"linked={m['linked_repositories']}  {m['server_url']}"
        )
        print(f"      setup example: {m['example_consumer_url']}  {m['example_config_file_path']}")

    case = selected_case(con, expected)
    in_search = any(m["tool_id"] == case["tool"]["tool_id"] for m in matches)
    setup = case["setup"]
    print("\nPart 2. The paper's selected case (chosen deliberately, not a search ranking)")
    print(f"  tool             {case['tool']['tool_name']} (source={case['tool']['source']}, reported by the directory)")
    print(f"  required inputs  {', '.join(case['required_inputs'])}")
    print(f"  input fields     {', '.join(case['input_fields'])}")
    print(f"  provider         {case['tool']['server_url']}")
    print(f"  consumer         {case['tool']['consumer_url']}")
    print(f"  setup file       {setup['config_file_path']}  command={setup['raw_command']}  args={setup['raw_args']}")
    print(f"  matching method  {setup['match_method']}")
    print(f"  in this search   {'yes' if in_search else 'no'}")
    print(
        "PASS: stored schema (valid and invalid inputs), setup declaration, and package mapping\n"
        "The declaration names a server to connect to. It does not show that the project called the tool."
    )

    write_json(
        output,
        {
            "release_revision": release.revision,
            "input_sha256": hashes,
            "search": {
                "term": args.term,
                "unit": "tool observation per source, on servers with at least one linked consuming repository",
                "tool_observations": len(matches),
                "servers": len(servers),
                "results": matches,
            },
            "selected_case": {
                "selection": "purposefully selected for the paper, not a population estimate",
                "found_by_this_search": in_search,
                **case,
            },
            "bounds": "Stored metadata and joins checked offline. No server was run. "
            "A declaration is not evidence of runtime use.",
        },
    )
    print(f"Wrote {output}")


if __name__ == "__main__":
    run(main)
