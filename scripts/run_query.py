"""Run a SQL file over the verified tables of one download group.

Every table of the group is checked against the pinned release, then exposed as
a DuckDB view with the table's name. The file may hold several statements. The
result of the last one is printed. Nothing is written.

Example:
  python scripts/run_query.py queries/pr_storage_checks.sql --group researcher --data-dir data
"""

from __future__ import annotations

import argparse
from pathlib import Path

from common import DEFAULT_DATA_DIR, GROUP_NAMES, ArtifactError, connect, load_release, plain, run


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("sql_file", type=Path)
    parser.add_argument("--group", choices=GROUP_NAMES, required=True, help="tables to verify and expose")
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR, help="default: <repository>/data")
    parser.add_argument("--limit", type=int, default=50, help="result rows to print, default 50")
    args = parser.parse_args()
    if not args.sql_file.is_file():
        raise ArtifactError(f"No SQL file at {args.sql_file}")

    con, _ = connect(load_release(), args.data_dir, args.group)
    cursor = con.execute(args.sql_file.read_text())
    if cursor.description is None:
        print("The last statement returned no rows.")
        return
    columns = [c[0] for c in cursor.description]
    rows = [plain(list(r)) for r in cursor.fetchall()]
    if not rows:
        print(f"No rows. Columns: {', '.join(columns)}")
        return
    if len(rows) == 1:
        width = max(map(len, columns))
        for name, value in zip(columns, rows[0]):
            print(f"{name:<{width}}  {value}")
        return
    print("\t".join(columns))
    for r in rows[: args.limit]:
        print("\t".join("" if v is None else str(v) for v in r))
    if len(rows) > args.limit:
        print(f"... {len(rows) - args.limit} more rows not shown (of {len(rows)}). Use --limit to show more.")


if __name__ == "__main__":
    run(main)
