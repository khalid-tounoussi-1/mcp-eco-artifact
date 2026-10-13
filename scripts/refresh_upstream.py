"""Optional: repeat the public GitHub inspection behind evidence/upstream-check.json.

Re-inspects the same consumer file revision, pull request, and reviews through
the public GitHub API, writes a new dated receipt, and compares it with the
frozen receipt. It never modifies evidence/upstream-check.json, and no other
script needs it. No credentials are used. The script makes 4 requests, within
GitHub's unauthenticated limit of 60 per hour.

The receipt stores hashes and selected launcher facts, not the inspected file.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from common import DEFAULT_OUTPUT_DIR, EVIDENCE_DIR, ArtifactError, run, write_json

API = "https://api.github.com/repos"
RAW = "https://raw.githubusercontent.com"
PACKAGE = "exa-mcp-server"


def get(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "mcp-eco-artifact"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.read()
    except urllib.error.URLError as error:
        raise ArtifactError(f"GitHub request failed for {url}: {error}")


def inspect(frozen: dict) -> dict:
    consumer = frozen["consumer"]
    owner_repo = consumer["repository_url"].removeprefix("https://github.com/")
    path = consumer["file_url"].split(f"/blob/{consumer['commit']}/", 1)[1]
    content = get(f"{RAW}/{owner_repo}/{consumer['commit']}/{path}")
    config = json.loads(content)
    declared = [s for s in config.get("mcpServers", {}).values() if PACKAGE in s.get("args", [])]
    if len(declared) != 1:
        raise ArtifactError(f"Expected one declaration of {PACKAGE} in {path}, found {len(declared)}")

    pr_url = frozen["pull_request"]["html_url"]
    server_repo, number = pr_url.removeprefix("https://github.com/").split("/pull/")
    pull = json.loads(get(f"{API}/{server_repo}/pulls/{number}"))
    issue = json.loads(get(f"{API}/{server_repo}/issues/{number}"))
    reviews = json.loads(get(f"{API}/{server_repo}/pulls/{number}/reviews"))
    return {
        "verified_at_utc": datetime.now(timezone.utc).isoformat(),
        "consumer": {
            "repository_url": consumer["repository_url"],
            "commit": consumer["commit"],
            "file_url": consumer["file_url"],
            "blob_sha": hashlib.sha1(b"blob %d\0" % len(content) + content).hexdigest(),
            "file_sha256": hashlib.sha256(content).hexdigest(),
            "exa_command": declared[0].get("command"),
            "exa_package_argument_present": True,
        },
        "pull_request": {
            "html_url": pull["html_url"],
            "pull_id": pull["id"],
            "issue_id": issue["id"],
            "title": pull["title"],
            "merged_at": pull["merged_at"],
            "merge_commit_sha": pull["merge_commit_sha"],
        },
        "reviews": [{"id": r["id"], "state": r["state"], "html_url": r["html_url"]} for r in reviews],
    }


def differences(frozen: dict, fresh: dict, prefix: str = "") -> list[str]:
    found = []
    for key in sorted(set(frozen) | set(fresh)):
        if key == "verified_at_utc":
            continue
        a, b = frozen.get(key), fresh.get(key)
        if isinstance(a, dict) and isinstance(b, dict):
            found += differences(a, b, f"{prefix}{key}.")
        elif a != b:
            found.append(f"{prefix}{key}: frozen {a!r}, now {b!r}")
    return found


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--output", type=Path, help="default: <repository>/outputs/upstream-check-<UTC time>.json")
    args = parser.parse_args()

    frozen = json.loads((EVIDENCE_DIR / "upstream-check.json").read_text())
    fresh = inspect(frozen)
    stamp = fresh["verified_at_utc"][:19].replace(":", "")
    output = (args.output or DEFAULT_OUTPUT_DIR / f"upstream-check-{stamp}.json").resolve()
    if output == (EVIDENCE_DIR / "upstream-check.json").resolve():
        raise ArtifactError("Refusing to overwrite the frozen receipt")
    output.parent.mkdir(parents=True, exist_ok=True)
    write_json(output, fresh)
    print(f"Wrote {output}")

    found = differences(frozen, fresh)
    if found:
        raise ArtifactError("GitHub now differs from the frozen receipt:\n  " + "\n  ".join(found))
    print(f"PASS: GitHub still matches the receipt dated {frozen['verified_at_utc']} (all fields but the date)")


if __name__ == "__main__":
    run(main)
