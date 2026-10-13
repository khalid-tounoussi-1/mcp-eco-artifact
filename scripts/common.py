"""Shared paths, pinned release evidence, and verified table access.

Every script takes the dataset identity from release/source.json. The three
evidence files that source.json names are checked against their SHA-256 hashes
before any of their contents is used. Parquet files are checked against the
pinned manifest before DuckDB reads them.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RELEASE_DIR = ROOT / "release"
QUERIES_DIR = ROOT / "queries"
EVIDENCE_DIR = ROOT / "evidence"
DEFAULT_DATA_DIR = ROOT / "data"
DEFAULT_OUTPUT_DIR = ROOT / "outputs"

# Tables each example reads. "all" is every file in the pinned manifest.
GROUPS: dict[str, tuple[str, ...]] = {}
GROUPS["listing"] = ("mcp_servers", "repo_server_usage")
GROUPS["engineer"] = GROUPS["listing"] + ("consumer_repos", "mcp_tools", "mcp_server_transports")
GROUPS["researcher"] = GROUPS["engineer"] + (
    "server_pull_requests",
    "client_pull_requests",
    "pr_reviews",
)
GROUP_NAMES = ("listing", "engineer", "researcher", "all")

EVIDENCE_FILES = (
    ("collection_metadata.json", "metadata_sha256"),
    ("schema.sql", "schema_sha256"),
    ("release-files.json", "manifest_sha256"),
)
FULL_REVISION = re.compile(r"[0-9a-f]{40}")


class ArtifactError(Exception):
    """An expected failure, reported to the user without a traceback."""


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


@dataclass(frozen=True)
class Release:
    repo_id: str
    revision: str
    source: dict
    metadata: dict
    files: dict[str, dict]  # table name -> manifest entry

    @property
    def tables(self) -> tuple[str, ...]:
        return tuple(self.metadata["table_row_counts"])

    def group(self, name: str) -> tuple[str, ...]:
        if name == "all":
            return self.tables
        if name not in GROUPS:
            raise ArtifactError(f"Unknown group {name!r}. Choose one of: {', '.join(GROUP_NAMES)}")
        return GROUPS[name]

    def size(self, tables) -> int:
        return sum(self.files[t]["size"] for t in tables)


def load_release(release_dir: Path = RELEASE_DIR) -> Release:
    """Read and check the pinned release evidence. Fails before any analysis."""
    source = json.loads((release_dir / "source.json").read_text())
    if not source.get("repo_id"):
        raise ArtifactError("release/source.json has no repo_id")
    if not FULL_REVISION.fullmatch(source.get("revision", "")):
        raise ArtifactError(
            "release/source.json must pin a full 40-character commit hash, "
            f"not {source.get('revision')!r}"
        )
    for filename, key in EVIDENCE_FILES:
        if sha256_file(release_dir / filename) != source[key]:
            raise ArtifactError(f"Pinned evidence file has changed: release/{filename}")

    metadata = json.loads((release_dir / "collection_metadata.json").read_text())
    rows = metadata["table_row_counts"]
    if not rows or any(type(n) is not int or n < 0 for n in rows.values()):
        raise ArtifactError("Expected nonnegative integer row counts in collection_metadata.json")
    if sum(rows.values()) != metadata["total_rows"]:
        raise ArtifactError("Release metadata total disagrees with its table counts")

    records = json.loads((release_dir / "release-files.json").read_text())
    by_path = {entry["path"]: entry for entry in records}
    if len(by_path) != len(records):
        raise ArtifactError("Duplicate paths in the pinned file manifest")
    if set(by_path) != {f"parquet/{table}.parquet" for table in rows}:
        raise ArtifactError("Metadata tables and the pinned file manifest disagree")
    for entry in records:
        if not entry.get("lfs_sha256") or type(entry.get("size")) is not int:
            raise ArtifactError(f"No pinned size and SHA-256 for {entry['path']}")
    files = {table: by_path[f"parquet/{table}.parquet"] for table in rows}
    return Release(source["repo_id"], source["revision"], source, metadata, files)


def table_path(data_dir: Path, table: str) -> Path:
    return data_dir / "parquet" / f"{table}.parquet"


def verify_file(release: Release, data_dir: Path, table: str) -> str:
    """Check one local Parquet file's size and SHA-256 against the manifest. Returns the hash."""
    path = table_path(data_dir, table)
    entry = release.files[table]
    if not path.is_file():
        raise ArtifactError(f"Missing {path}")
    if path.stat().st_size != entry["size"]:
        raise ArtifactError(
            f"{path} has {path.stat().st_size} bytes, the pinned release has {entry['size']}. "
            "The file was not changed. Delete it and download it again."
        )
    digest = sha256_file(path)
    if digest != entry["lfs_sha256"]:
        raise ArtifactError(
            f"SHA-256 of {path} differs from the pinned release. "
            "The file was not changed. Delete it and download it again."
        )
    return digest


def connect(release: Release, data_dir: Path, group: str):
    """Verify every file of a group, expose each table as a DuckDB view, and load queries/macros.sql."""
    import duckdb

    tables = release.group(group)
    missing = [t for t in tables if not table_path(data_dir, t).is_file()]
    if missing:
        raise ArtifactError(
            f"Missing {len(missing)} table(s) in {data_dir / 'parquet'}: {', '.join(missing)}.\n"
            f"Run: python scripts/download_data.py --group {group} --data-dir {data_dir}"
        )
    hashes = {table: verify_file(release, data_dir, table) for table in tables}
    con = duckdb.connect()
    for table in tables:
        con.read_parquet(str(table_path(data_dir, table))).create_view(table)
    run_sql_file(con, "macros.sql")
    return con, hashes


def fetch(con, sql: str, params=()) -> list[dict]:
    cursor = con.execute(sql, params)
    columns = [c[0] for c in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def run_sql_file(con, name: str) -> None:
    con.execute((QUERIES_DIR / name).read_text())


def output_path(arg: Path | None, default_name: str, data_dir: Path) -> Path:
    """Resolve an output path and keep generated files out of the data directory."""
    path = (arg or DEFAULT_OUTPUT_DIR / default_name).resolve()
    if path.is_relative_to(data_dir.resolve()):
        raise ArtifactError(f"Refusing to write {path} inside the data directory {data_dir}")
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def write_json(path: Path, payload) -> None:
    path.write_text(json.dumps(payload, indent=2, default=str, ensure_ascii=False) + "\n")


def plain(value):
    """Convert DuckDB values (UUID, datetime) to JSON-friendly values."""
    if isinstance(value, dict):
        return {k: plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [plain(v) for v in value]
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    return str(value)


def run(main) -> None:
    """Run a script entry point, turning expected failures into short messages."""
    try:
        main()
    except ArtifactError as error:
        print(f"error: {error}", file=sys.stderr)
        sys.exit(2)
