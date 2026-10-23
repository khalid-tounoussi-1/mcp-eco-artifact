"""Check the selected GitHub and arXiv records without invoking MCP tools."""
from __future__ import annotations

import json

from checks import require, validate_examples
from common import EVIDENCE_DIR, Release


def expected_case(release: Release, name: str) -> dict:
    evidence = json.loads((EVIDENCE_DIR / "github-arxiv-expected.json").read_text())
    require(evidence["release_revision"] == release.revision, "Case evidence belongs to another release")
    return evidence[name]


def check_schemas(rows: list[dict], expected: list[dict]) -> list[dict]:
    """Reject missing, extra, duplicated, or changed selected tool observations."""
    require(sorted(r["tool_name"] for r in rows) == sorted(r["tool_name"] for r in expected),
            "Selected tool observations are missing, duplicated, or unexpected")
    specifications = {r["tool_name"]: r for r in expected}
    result = []
    for row in rows:
        spec = specifications[row["tool_name"]]
        schema_text = row["input_json_schema"]
        require(schema_text is not None, "Selected tool has no stored input schema")
        schema = json.loads(schema_text)
        require(schema == spec["schema"], f"Changed schema: {row['tool_name']}")
        if "tool_id" in row:
            require(str(row["tool_id"]) == spec["tool_id"], "Unexpected selected tool identity")
        if "source" in row:
            require(row["source"] == "probe", "Selected capability is not a probe observation")
        valid = spec["example_input"]
        invalid_type = dict(valid)
        invalid_type[schema["required"][0]] = []
        validate_examples(schema_text, valid=[valid], invalid=[{}, invalid_type])
        result.append({"tool_name": row["tool_name"], "source": "probe",
                       "input_json_schema": schema, "example_input": valid})
    return result
