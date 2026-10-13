# Reproduction

This page maps each item of the paper that this repository can check to its
command, and records a tested run. Run every command from the repository root,
inside the environment created in the README.

## Paper items

| Paper item | Command | Query or logic | Files read | Output | Success condition |
| --- | --- | --- | --- | --- | --- |
| Listing 1, configured repositories per candidate server | `python scripts/paper_listing.py --data-dir data --output outputs/listing.csv` | `queries/paper_listing.sql` | group `listing` | `outputs/listing.csv` | Every `server_id`, name, and count equals `evidence/listing-expected.csv` |
| Story "For a software engineer" | `python scripts/engineer_example.py --data-dir data --output outputs/engineer.json` | `queries/linked_tools.sql`, `scripts/checks.py` | group `engineer` | `outputs/engineer.json` | Every check of the selected case passes (see [examples.md](examples.md)) |
| Story "For a researcher" | `python scripts/researcher_example.py --data-dir data --output outputs/researcher.json` | `queries/server_changes.sql`, `scripts/checks.py` | group `researcher` | `outputs/researcher.json` | Identity, review, timing, and receipt checks pass |
| Inventory table and record counts in the abstract | `python scripts/verify_release.py --data-dir data --check` | Parquet footers | group `all` | JSON report on standard output | All 19 files match the pinned sizes and hashes, and every footer count matches the release metadata |
| Every inventory number in the manuscript | `python scripts/check_claims.py --data-dir data` | `release/claims.yaml` | group `all` | one line per claim | 22 of 22 claims regenerated without drift |
| Export date, 2026-06-23 UTC | `python scripts/verify_release.py --emit export_date` | `collected_at_utc` in the pinned metadata | `release/` only | `20260623` | Equals the claim. This value is read from metadata, not regenerated from data. |

Items this repository cannot check: the collection and matching stages, the
capability probes, and the public GitHub inspection itself. The inspection is
replayed from `evidence/upstream-check.json`. `scripts/refresh_upstream.py`
repeats it live as an optional step.

## How the expected listing was produced

`evidence/listing-expected.csv` holds the full output of the paper's own
listing code. The code was copied verbatim from the manuscript with two edits.
The query result was bound to a variable, and `.show()`, which prints only the
first rows, was replaced by `.fetchall()`. The code downloaded its two tables
from Hugging Face at the pinned revision, with an empty cache and no token. The
rows were sorted by count, descending, then by `server_id`, and written as CSV.

The result has 984 rows, one per candidate server with at least one resolved
repository/server pair. Their counts sum to 5,138 distinct resolved pairs. A
second run of the same code produced a byte-identical file. The comparison in
`scripts/paper_listing.py` ignores row order, because the paper's listing does
not order tied rows.
