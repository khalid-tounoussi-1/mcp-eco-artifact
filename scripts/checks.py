"""Identity and schema checks shared by the worked examples.

Each check raises CheckFailed with a short reason. None of them runs an MCP
server or executes a command found in a record.
"""

from __future__ import annotations

import hashlib
import json

from jsonschema import Draft7Validator

from common import ArtifactError, fetch


class CheckFailed(ArtifactError):
    pass


def require(condition, message: str) -> None:
    if not condition:
        raise CheckFailed(message)


def one(rows: list[dict], context: str) -> dict:
    require(len(rows) == 1, f"{context}: expected one record, found {len(rows)}")
    return rows[0]


def text_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def required_inputs(schema_text: str | None):
    """Required input names from a stored JSON Schema string.

    None means no stored schema. That is a missing observation, not a tool
    without inputs.
    """
    if schema_text is None:
        return None
    try:
        schema = json.loads(schema_text)
    except json.JSONDecodeError:
        return "unparseable schema"
    return schema.get("required", []) if isinstance(schema, dict) else "unparseable schema"


def validate_examples(schema_text: str, valid: list[dict], invalid: list[dict]) -> Draft7Validator:
    """Check that the schema is well formed, accepts each valid input and rejects each invalid one."""
    schema = json.loads(schema_text)
    Draft7Validator.check_schema(schema)
    validator = Draft7Validator(schema)
    for example in valid:
        require(validator.is_valid(example), f"stored schema rejects valid input {example}")
    for example in invalid:
        require(not validator.is_valid(example), f"stored schema accepts invalid input {example}")
    return validator


def observations_by_source(con, server_id) -> dict[str, int]:
    """Tool observations per source for one server.

    A source with no rows is absent from the result. The release cannot tell
    an unprobed server from one with no tools, so absence is not zero.
    """
    rows = fetch(
        con,
        "SELECT source, COUNT(*) AS n FROM mcp_tools WHERE server_id = ? GROUP BY source ORDER BY source",
        [server_id],
    )
    return {r["source"]: r["n"] for r in rows}


def unique_server_pr(con, pr_url: str) -> dict:
    """Return the one server PR with this URL, after checking its identifier.

    Reviews reference pr_id without a declared foreign key. The release can
    store one pull request twice under two pr_id values, and the two PR tables
    use the same numeric column. The selected case is accepted only in the
    simplest situation: one server row has the URL in any spelling (pr_key in
    queries/macros.sql), its pr_id occurs once in the server table, and neither
    the URL nor the pr_id appears in the client table. Any twin row, second
    spelling, or reused id fails the check.
    """
    pr = one(
        fetch(
            con,
            """SELECT pr_id, server_id, pr_url, title, body_text, state, merged_at
               FROM server_pull_requests WHERE pr_key(pr_url) = pr_key(?)""",
            [pr_url],
        ),
        f"server pull request {pr_url}, in any URL spelling",
    )
    same_id = fetch(con, "SELECT pr_url FROM server_pull_requests WHERE pr_id = ?", [pr["pr_id"]])
    require(len(same_id) == 1, f"pr_id {pr['pr_id']} appears {len(same_id)} times in server_pull_requests")
    client_id = fetch(con, "SELECT pr_url FROM client_pull_requests WHERE pr_id = ?", [pr["pr_id"]])
    require(not client_id, f"pr_id {pr['pr_id']} also appears in client_pull_requests")
    client_url = fetch(con, "SELECT pr_id FROM client_pull_requests WHERE pr_key(pr_url) = pr_key(?)", [pr_url])
    require(not client_url, f"{pr_url} also appears in client_pull_requests")
    return pr


def reviews_for(con, pr_id: int) -> list[dict]:
    return fetch(
        con,
        "SELECT review_id, review_state FROM pr_reviews WHERE pr_id = ? ORDER BY review_id",
        [pr_id],
    )


def check_receipt(receipt: dict, *, consumer_url: str, pr: dict, reviews: list[dict]) -> None:
    """Replay the dated GitHub inspection receipt against the frozen records."""
    consumer = receipt["consumer"]
    require(consumer["repository_url"] == consumer_url, "receipt inspected a different consumer repository")
    require(
        consumer["exa_command"] == "npx" and consumer["exa_package_argument_present"],
        "receipt does not record the npx launcher with the exa-mcp-server package",
    )
    upstream = receipt["pull_request"]
    require(upstream["html_url"] == pr["pr_url"], "receipt inspected a different pull request")
    require(upstream["issue_id"] == pr["pr_id"], "frozen pr_id differs from the GitHub issue ID")
    require(
        {(r["review_id"], r["review_state"]) for r in reviews}
        == {(r["id"], r["state"]) for r in receipt["reviews"]},
        "frozen review IDs or states differ from the receipt",
    )
