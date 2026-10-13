"""SYNTHETIC records for unit tests only.

Every server, repository, tool, pull request, and review below is invented.
These records exercise counting rules and failure paths. They cannot support
any statement about MCP-Eco or the MCP ecosystem. URLs have the github.com
shape, because pr_key only normalizes github.com URLs, but their owner,
"synthetic", is made up. No test contacts GitHub.

build() writes Parquet files with the column types of the real release (UUID
identifiers, JSON stored as strings) and a release/ directory whose evidence
hashes are computed from those files, so load_release() accepts it.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

REVISION = "0" * 40


def uid(name: str) -> bytes:
    return uuid.uuid5(uuid.NAMESPACE_URL, f"synthetic:{name}").bytes


def sid(name: str) -> str:
    return str(uuid.UUID(bytes=uid(name)))


SCHEMA = json.dumps({
    "type": "object",
    "required": ["query"],
    "properties": {"query": {"type": "string"}, "limit": {"type": "number"}},
    "additionalProperties": False,
})


def _uuids(names):
    return pa.array([uid(n) if n else None for n in names], type=pa.uuid())


def tables() -> dict[str, pa.Table]:
    t = datetime(2026, 1, 1)
    return {
        # S1 and S2 are declared. S3 has no declarations. S4 ties with S2.
        "mcp_servers": pa.table({
            "server_id": _uuids(["S1", "S2", "S3", "S4"]),
            "repository_url": ["https://github.com/synthetic/s1", "https://github.com/synthetic/s2",
                               "https://github.com/synthetic/s3", "https://github.com/synthetic/s4"],
            "server_name": ["alpha", "beta", "gamma", "delta"],
        }),
        "consumer_repos": pa.table({
            "repo_id": pa.array([1, 2, 3], type=pa.int64()),
            "repository_url": ["https://github.com/synthetic/r1", "https://github.com/synthetic/r2", "https://github.com/synthetic/r3"],
        }),
        # R1 declares S1 in two files (one pair). R3 has an unmatched declaration.
        "repo_server_usage": pa.table({
            "usage_id": _uuids(["U1", "U2", "U3", "U4", "U5", "U6"]),
            "repo_id": pa.array([1, 1, 2, 1, 3, 2], type=pa.int64()),
            "server_id": _uuids(["S1", "S1", "S1", "S2", None, "S4"]),
            "raw_server_name": ["alpha", "alpha", "alpha", "beta", "unknown", "delta"],
            "config_file_path": [".mcp.json", ".cursor/mcp.json", ".mcp.json", ".mcp.json", ".mcp.json", ".mcp.json"],
            "raw_command": ["npx"] * 6,
            "raw_args": ['["-y", "alpha"]', '["-y", "alpha"]', '["-y", "alpha"]', '["beta"]', '["x"]', '["delta"]'],
            "match_method": ["v1", "v1", "v1", "v1", None, "v1"],
        }),
        # web_search on S1 is observed by both sources. S2 has directory rows only.
        "mcp_tools": pa.table({
            "tool_id": _uuids(["T1", "T2", "T3", "T4"]),
            "server_id": _uuids(["S1", "S1", "S1", "S2"]),
            "tool_name": ["web_search", "web_search", "fetch_page", "lookup"],
            "original_description": ["Search the web", "Search the web", "Fetch a page", "Look up a web search index"],
            "input_json_schema": [SCHEMA, SCHEMA, None, "{not json"],
            "source": ["probe", "glama", "glama", "glama"],
        }),
        "mcp_server_transports": pa.table({
            "transport_id": _uuids(["X1", "X2", "X3"]),
            "server_id": _uuids(["S1", "S2", "S4"]),
            "package_identifier": ["alpha", "beta", "beta"],
        }),
        # pull/1 (101) is stored once. pull/2 (102) reuses an id of a client PR.
        # pull/3 (103) has no review rows. pull/4 is stored twice, as 104 under
        # S1 and 105 under S4, and the two rows disagree on state. pull/8 (108)
        # is also a client PR under 208, spelled with a capital S. pull/9 is
        # spelled two ways: 109 with a capital S, 110 with a /tree/ segment.
        # 106 is stored for two URLs.
        "server_pull_requests": pa.table({
            "pr_id": pa.array([101, 102, 103, 104, 105, 106, 106, 108, 109, 110], type=pa.int64()),
            "server_id": _uuids(["S1", "S1", "S1", "S1", "S4", "S1", "S1", "S1", "S1", "S1"]),
            "pr_url": ["https://github.com/synthetic/s1/pull/1", "https://github.com/synthetic/s1/pull/2",
                       "https://github.com/synthetic/s1/pull/3", "https://github.com/synthetic/s1/pull/4",
                       "https://github.com/synthetic/s1/pull/4", "https://github.com/synthetic/s1/pull/6",
                       "https://github.com/synthetic/s1/pull/7", "https://github.com/synthetic/s1/pull/8",
                       "https://github.com/synthetic/S1/pull/9", "https://github.com/synthetic/s1/tree/main/pkg/pull/9"],
            "title": ["Rename query in web_search", "Tidy query docs", "Query limits", "Query twin",
                      "Query twin", "id a", "id b", "Agent query fix", "Query spelled twice", "Query spelled twice"],
            "body_text": ["Changes the query input of web_search.", "query", None, "", "", "", "", "", "", ""],
            "state": ["MERGED", "MERGED", "OPEN", "OPEN", "CLOSED", "OPEN", "OPEN", "MERGED", "OPEN", "OPEN"],
            "created_at": [t] * 10,
            "merged_at": [t, t, None, None, None, None, None, t, None, None],
        }),
        "client_pull_requests": pa.table({
            "pr_id": pa.array([102, 208], type=pa.int64()),
            "repo_id": pa.array([1, 1], type=pa.int64()),
            "pr_url": ["https://github.com/synthetic/r1/pull/9", "https://github.com/synthetic/S1/pull/8"],
            "title": ["client change", "Agent query fix"],
            "body_text": ["", ""],
            "state": ["OPEN", "MERGED"],
            "created_at": [t, t],
            "merged_at": [None, t],
        }),
        # Reviews of pull/4 sit under both of its ids. The review of pull/8 sits
        # under its client id only, that of pull/9 under its /tree/ spelling.
        "pr_reviews": pa.table({
            "review_id": pa.array([1001, 1002, 1003, 1004, 1005, 1006, 1007], type=pa.int64()),
            "pr_id": pa.array([101, 101, 102, 104, 105, 208, 110], type=pa.int64()),
            "review_state": ["COMMENTED", "APPROVED", "APPROVED", "APPROVED", "COMMENTED", "APPROVED", "APPROVED"],
        }),
    }


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_release_dir(release_dir: Path, data_dir: Path, names) -> None:
    """Write release evidence describing the Parquet files under data_dir."""
    release_dir.mkdir(parents=True, exist_ok=True)
    metadata = {
        "collected_at_utc": "2026-01-01T00:00:00+00:00",
        "table_row_counts": {n: pq.ParquetFile(data_dir / "parquet" / f"{n}.parquet").metadata.num_rows for n in names},
    }
    metadata["total_rows"] = sum(metadata["table_row_counts"].values())
    manifest = []
    for n in names:
        path = data_dir / "parquet" / f"{n}.parquet"
        manifest.append({"path": f"parquet/{n}.parquet", "size": path.stat().st_size,
                         "blob_id": "synthetic", "lfs_sha256": _sha256(path)})
    (release_dir / "collection_metadata.json").write_text(json.dumps(metadata))
    (release_dir / "release-files.json").write_text(json.dumps(manifest))
    (release_dir / "schema.sql").write_text("-- synthetic\n")
    (release_dir / "source.json").write_text(json.dumps({"repo_id": "synthetic/not-a-dataset", "revision": REVISION}))
    rehash(release_dir)


def rehash(release_dir: Path) -> None:
    """Record the current evidence hashes in source.json, as a release author would."""
    source = json.loads((release_dir / "source.json").read_text())
    for filename, key in (("collection_metadata.json", "metadata_sha256"), ("schema.sql", "schema_sha256"),
                          ("release-files.json", "manifest_sha256")):
        source[key] = _sha256(release_dir / filename)
    (release_dir / "source.json").write_text(json.dumps(source))


def build(root: Path) -> tuple[Path, Path]:
    """Write synthetic Parquet files and matching evidence. Returns (release_dir, data_dir)."""
    data_dir = root / "data"
    (data_dir / "parquet").mkdir(parents=True)
    built = tables()
    for name, table in built.items():
        pq.write_table(table, data_dir / "parquet" / f"{name}.parquet")
    release_dir = root / "release"
    write_release_dir(release_dir, data_dir, list(built))
    return release_dir, data_dir
