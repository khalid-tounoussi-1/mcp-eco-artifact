"""Reproduce the paper's Listing 1 on the pinned release.

Counts distinct configured repositories per candidate server. A configured
repository has at least one harvested configuration declaration matched to the
server. The count is not an installation count, an active-user count, or a
measure of runtime use.

The full result is written to a CSV file and compared, key by key, with
evidence/listing-expected.csv. That file holds the full output of the original
listing in the paper.

--check-references adds the referential checks of the dataset card's pandas
example. It is an extension, not part of the paper listing, and needs the
engineer group.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from common import (
    DEFAULT_DATA_DIR,
    EVIDENCE_DIR,
    QUERIES_DIR,
    ArtifactError,
    connect,
    fetch,
    load_release,
    output_path,
    run,
)

COLUMNS = ("server_id", "server_name", "configured_repositories")
EXPECTED = EVIDENCE_DIR / "listing-expected.csv"


def listing(con) -> list[dict]:
    rows = fetch(con, (QUERIES_DIR / "paper_listing.sql").read_text())
    return [{**r, "server_id": str(r["server_id"])} for r in rows]


def read_csv(path: Path) -> dict[str, tuple[str, int]]:
    with path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    keyed = {r["server_id"]: (r["server_name"], int(r["configured_repositories"])) for r in rows}
    if len(keyed) != len(rows):
        raise ArtifactError(f"Duplicate server_id in {path}")
    return keyed


def compare(rows: list[dict], expected: dict[str, tuple[str, int]]) -> list[str]:
    """Return differences in keys, names, or counts. Row order is not compared."""
    observed = {r["server_id"]: (r["server_name"], r["configured_repositories"]) for r in rows}
    problems = [f"{len(rows) - len(observed)} duplicate server_id rows in the result"] if len(observed) != len(rows) else []
    problems += [f"missing server_id {k}" for k in sorted(expected.keys() - observed.keys())]
    problems += [f"unexpected server_id {k}" for k in sorted(observed.keys() - expected.keys())]
    problems += [
        f"{k}: expected {expected[k]}, found {observed[k]}"
        for k in sorted(expected.keys() & observed.keys())
        if expected[k] != observed[k]
    ]
    return problems


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR, help="default: <repository>/data")
    parser.add_argument("--output", type=Path, help="CSV path, default: <repository>/outputs/listing.csv")
    parser.add_argument("--top", type=int, default=20, help="rows to print (the CSV holds all rows)")
    parser.add_argument("--check-references", action="store_true", help="also check that resolved pairs reference existing records")
    args = parser.parse_args()

    release = load_release()
    output = output_path(args.output, "listing.csv", args.data_dir)
    con, _ = connect(release, args.data_dir, "engineer" if args.check_references else "listing")
    rows = listing(con)
    write_csv(output, rows)

    print(f"{'configured_repositories':>23}  server_name  (server_id)")
    for r in rows[: args.top]:
        print(f"{r['configured_repositories']:>23}  {r['server_name']}  ({r['server_id']})")
    context = fetch(
        con,
        """SELECT (SELECT COUNT(*) FROM mcp_servers) AS candidates,
                  COUNT(*) AS declarations,
                  COUNT(*) FILTER (WHERE server_id IS NULL) AS unmatched
           FROM repo_server_usage""",
    )[0]
    print(
        f"... {len(rows)} rows written to {output}, one per candidate server with at least one\n"
        f"matched declaration. The release holds {context['candidates']} candidate server records."
    )
    print(
        "Unit: distinct consuming repositories with at least one matched configuration declaration.\n"
        f"{context['unmatched']} of {context['declarations']} declaration rows have no matched server_id "
        "and are excluded. This is not installation or runtime use."
    )

    problems = compare(rows, read_csv(EXPECTED))
    if problems:
        shown = "\n  ".join(problems[:20])
        raise ArtifactError(f"{len(problems)} difference(s) from {EXPECTED.name}:\n  {shown}")
    print(f"PASS: all {len(rows)} server_id keys, names and counts match {EXPECTED.relative_to(EXPECTED.parents[1])}")

    if args.check_references:
        check = fetch(con, (QUERIES_DIR / "reference_checks.sql").read_text())[0]
        print(
            f"Reference check: {check['resolved_pairs']} resolved repository/server pairs, "
            f"{check['pairs_without_consumer_record']} without a consumer_repos record, "
            f"{check['pairs_without_server_record']} without an mcp_servers record"
        )
        if check["pairs_without_consumer_record"] or check["pairs_without_server_record"]:
            raise ArtifactError("Some resolved pairs reference missing records. Check the release files.")
        print("PASS: every resolved pair references existing consumer and server records")


if __name__ == "__main__":
    run(main)
