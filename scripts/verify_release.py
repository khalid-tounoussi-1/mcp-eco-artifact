"""Verify local files of the pinned release and regenerate its record counts.

--check verifies the complete release. All 19 Parquet files must be present.
Each file's size and SHA-256 hash are checked against release/release-files.json,
and each table's record count is read from its Parquet footer and compared with
release/collection_metadata.json.

--check --group G verifies only the files of one download group. Its output
says that the complete release was not verified.

--emit prints one inventory number for release/claims.yaml. The record-count
metrics need all 19 files and check their sizes and hashes first, like
--check. export_date is read from the pinned metadata and needs no data file.

Counts describe stored table rows, not validated MCP entities. No database is
queried.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import pyarrow.parquet as pq

from common import (
    DEFAULT_DATA_DIR,
    GROUP_NAMES,
    ArtifactError,
    Release,
    load_release,
    output_path,
    run,
    table_path,
    verify_file,
    write_json,
)

UNIT = "stored table row, without cross-table entity deduplication"


def footer_counts(release: Release, data_dir: Path, tables) -> dict[str, int]:
    missing = [t for t in tables if not table_path(data_dir, t).is_file()]
    if missing:
        raise ArtifactError(
            f"Missing {len(missing)} of {len(tables)} files in {data_dir / 'parquet'}: {', '.join(missing)}.\n"
            f"Download revision {release.revision} of {release.repo_id}, for example with "
            f"python scripts/download_data.py --group all --data-dir {data_dir}"
        )
    observed = {}
    for table in tables:
        verify_file(release, data_dir, table)  # size and SHA-256 before the footer is read
        observed[table] = pq.ParquetFile(table_path(data_dir, table)).metadata.num_rows
        expected = release.metadata["table_row_counts"][table]
        if observed[table] != expected:
            raise ArtifactError(f"Record-count mismatch in {table}: footer {observed[table]}, metadata {expected}")
    return observed


def emit(release: Release, data_dir: Path, metric: str) -> int:
    if metric == "export_date":
        # Read from the pinned metadata file, not regenerated from Parquet files.
        stamp = datetime.fromisoformat(release.metadata["collected_at_utc"])
        return int(stamp.astimezone(timezone.utc).strftime("%Y%m%d"))
    rows = footer_counts(release, data_dir, release.tables)
    if metric == "table_count":
        return len(rows)
    if metric == "total_rows":
        return sum(rows.values())
    if metric.startswith("rows.") and metric[5:] in rows:
        return rows[metric[5:]]
    raise ArtifactError(f"Unknown metric {metric!r}. Use table_count, total_rows, export_date, or rows.<table>")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR, help="default: <repository>/data")
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--check", action="store_true", help="verify file hashes and footer counts")
    action.add_argument("--emit", metavar="METRIC", help="table_count, total_rows, export_date, or rows.<table>")
    parser.add_argument("--group", choices=GROUP_NAMES, default="all", help="with --check: verify one download group only")
    parser.add_argument("--output", type=Path, help="with --check: also write the report to this JSON file")
    args = parser.parse_args()
    release = load_release()

    if args.emit:
        print(emit(release, args.data_dir, args.emit))
        return

    tables = release.group(args.group)
    complete = set(tables) == set(release.tables)
    rows = footer_counts(release, args.data_dir, tables)
    report = {
        "repo_id": release.repo_id,
        "revision": release.revision,
        "scope": "complete release" if complete else f"subset: group {args.group!r}",
        "files_verified": len(rows),
        "files_in_release": len(release.tables),
        "complete_release_verified": complete,
        "checks": "file size, SHA-256 hash, and Parquet footer record count per file",
        "table_row_counts": rows,
        # A subset sum is not the release total, so it gets its own key.
        ("total_rows" if complete else "subset_rows"): sum(rows.values()),
        "unit": UNIT,
        "semantic_membership_validated": False,
    }
    print(json.dumps(report, indent=2))
    if args.output:
        write_json(output_path(args.output, "inventory.json", args.data_dir), report)
    if complete:
        print(f"PASS: all {len(rows)} files of revision {release.revision} match the pinned release")
    else:
        print(
            f"PASS for a subset only: {len(rows)} of {len(release.tables)} files match. "
            "The complete release has not been verified."
        )


if __name__ == "__main__":
    run(main)
