"""Researcher story: from a server's tool to a development discussion.

Part 1 starts from a server and searches its stored pull request titles and
bodies for --term, such as a tool name or an input field. It works for any
server URL and term.

Part 2 checks the case used in the paper: Exa's pull request 237, which
discusses removing livecrawl from the web_search_exa tool schema. That case was
selected deliberately. It is an assertion target, not a sample.

Part 3 replays evidence/upstream-check.json, a dated receipt of a separate
public GitHub inspection. This replay is offline. It is not a fresh check.

The tool observation and the pull request were collected at different times.
This example does not establish an interface history, present compatibility,
or a current defect. An approval does not establish tested correctness.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from checks import check_receipt, observations_by_source, one, require, reviews_for, unique_server_pr
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

SEARCH_SQL = "SELECT * FROM server_pr_search(?, ?) ORDER BY created_at, pr_key"


def describe(row: dict) -> str:
    """One line of status for a pull request gathered from all its stored rows."""
    merged = row["merged_at_values"]
    if merged:
        status = "merged " + " / ".join(merged)
    else:
        status = "state " + ("/".join(row["states"]) or "unknown")
    if len(merged) > 1 or len(row["states"]) > 1:
        status += " (stored rows disagree)"
    stored = row["server_rows"] + row["client_rows"]
    if stored > 1:
        status += f"  stored as {stored} rows, pr_id {', '.join(map(str, row['pr_ids']))}"
    if not row["review_attribution_clean"]:
        return status + "  reviews not attributed (a pr_id belongs to another pull request)"
    if row["review_rows"] is None:
        return status + "  no review rows recorded"
    return status + f"  {row['review_rows']} review rows, {row['approved_review_rows']} approved"


def selected_case(con, expected: dict, tool_id: str, receipt: dict) -> dict:
    """Port of the identity checks behind the paper's researcher story."""
    pr = unique_server_pr(con, expected["pull_request"]["pr_url"])
    tool = one(fetch(con, "SELECT discovered_at FROM mcp_tools WHERE tool_id = ?", [tool_id]), "selected tool")
    body = pr.pop("body_text") or ""
    for term in expected["mentions"]:
        require(term in body, f"pull request body does not mention {term}")
    require(pr["merged_at"] is not None, "pull request is not recorded as merged")
    require(tool["discovered_at"] > pr["merged_at"], "tool observation does not postdate the merge")
    observed = plain({k: pr[k] for k in expected["pull_request"]})
    require(observed == expected["pull_request"], "pull request differs from the expected record")

    reviews = plain(reviews_for(con, pr["pr_id"]))
    require(reviews == expected["reviews"], "reviews differ from the expected records")
    require(any(r["review_state"] == "APPROVED" for r in reviews), "no recorded approval")

    check_receipt(receipt, consumer_url=expected["consumer_url"], pr=pr, reviews=reviews)
    upstream = receipt["pull_request"]
    require(upstream["pull_id"] != pr["pr_id"], "receipt pull_id unexpectedly equals the frozen pr_id")
    return {
        "pull_request": plain(pr),
        "mentions_checked": expected["mentions"],
        "reviews": reviews,
        "timing": {
            "tool_observation_discovered_at": str(tool["discovered_at"]),
            "pull_request_merged_at": str(pr["merged_at"]),
            "note": "The stored schema was collected after this pull request merged, yet still lists "
            "livecrawl. The records cannot show which interface a project encountered.",
        },
        "identifier_note": (
            f"The frozen pr_id {pr['pr_id']} is the GitHub issue ID. The REST pull request ID is "
            f"{upstream['pull_id']}. Reviews are attributed here because the URL and pr_id are unique "
            "in server_pull_requests and absent from client_pull_requests, not because numbers match."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR, help="default: <repository>/data")
    parser.add_argument("--output", type=Path, help="JSON path, default: <repository>/outputs/researcher.json")
    parser.add_argument("--server-url", help="server repository URL, default: the paper's Exa server")
    parser.add_argument("--term", default="livecrawl", help="text to find in pull request titles or bodies")
    parser.add_argument("--limit", type=int, default=10, help="search results to print")
    args = parser.parse_args()

    evidence = json.loads((EVIDENCE_DIR / "exa-expected.json").read_text())
    expected = evidence["researcher"]
    receipt = json.loads((EVIDENCE_DIR / "upstream-check.json").read_text())
    release = load_release()
    output = output_path(args.output, "researcher.json", args.data_dir)
    con, hashes = connect(release, args.data_dir, "researcher")
    run_sql_file(con, "server_changes.sql")

    server_url = args.server_url or expected["server_url"]
    server = one(
        fetch(con, "SELECT server_id, server_name FROM mcp_servers WHERE repository_url = ?", [server_url]),
        f"candidate server {server_url}",
    )
    tools = observations_by_source(con, server["server_id"])
    matches = plain(fetch(con, SEARCH_SQL, [server["server_id"], args.term]))

    print(f"Part 1. Pull requests of {server_url} mentioning {args.term!r}")
    print(f"Stored tool observations by source: {tools or 'none recorded'} (a missing source is not zero)")
    stored_rows = sum(m["server_rows"] + m["client_rows"] for m in matches)
    print(
        f"{len(matches)} pull requests match in their title or body, gathered from {stored_rows} "
        "stored rows. One line per pull request (pr_key)."
    )
    if not matches:
        print("  No match. Try a tool name or an input field of this server.")
    for m in matches[: args.limit]:
        spellings = f"  ({len(m['pr_urls'])} URL spellings)" if len(m["pr_urls"]) > 1 else ""
        print(f"  {m['pr_key']}{spellings}  {describe(m)}")
        print(f"      {m['title']}")

    case = selected_case(con, expected, evidence["engineer"]["tool"]["tool_id"], receipt)
    pr = case["pull_request"]
    print("\nPart 2. The paper's selected case (chosen deliberately, not a sample)")
    print(f"  pull request     {pr['pr_url']}")
    print(f"  title            {pr['title']}")
    print(f"  merged at        {pr['merged_at']}")
    print(f"  mentions         {', '.join(case['mentions_checked'])}")
    print(f"  reviews          {', '.join(r['review_state'] for r in case['reviews'])}")
    print(f"  identifiers      {case['identifier_note']}")
    print(f"  timing           tool observation {case['timing']['tool_observation_discovered_at']}, "
          f"pull request merged {case['timing']['pull_request_merged_at']}")
    print(f"                   {case['timing']['note']}")
    print("PASS: pull request identity, cross-table uniqueness, and review attribution")
    print(f"\nPart 3. Offline replay of the GitHub receipt dated {receipt['verified_at_utc']}")
    print("PASS: consumer setup facts, pull request identity, and review IDs and states match the receipt")
    print("The receipt records a past inspection. It is not a fresh GitHub check.")

    write_json(
        output,
        {
            "release_revision": release.revision,
            "input_sha256": hashes,
            "server": plain({"server_url": server_url, **server}),
            "tool_observations_by_source": tools,
            "search": {
                "term": args.term,
                "unit": "pull request of the server (one pr_key), matched by title or body text, "
                "with all its stored rows in both pull request tables gathered",
                "pull_requests": len(matches),
                "stored_rows": stored_rows,
                "results": matches,
            },
            "selected_case": {"selection": "purposefully selected for the paper, not a population estimate", **case},
            "receipt_replay": {
                "receipt": "evidence/upstream-check.json",
                "verified_at_utc": receipt["verified_at_utc"],
                "fresh_github_check": False,
            },
            "bounds": "The tool observation and the pull request were collected at different times. "
            "No interface history, compatibility, current defect, or tested correctness is established.",
        },
    )
    print(f"Wrote {output}")


if __name__ == "__main__":
    run(main)
