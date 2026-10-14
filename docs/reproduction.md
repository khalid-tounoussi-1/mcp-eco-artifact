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

## Tested run

| | |
| --- | --- |
| Code revision | `7228e238ea62cd46c88562ad700023e5c0e65f6b`. The next commit adds this record and changes no code. |
| Data revision | `c8edfd4bdf51b15ea95d6b0ede5dec97945f398a` |
| Date | 2026-10-13, from 21:52:36 to 21:56:41 UTC |
| Machine | macOS 27.0.1 on arm64 |
| Python | 3.12.13, with `requirements.lock` (duckdb 1.5.6, huggingface_hub 2.2.0, pyarrow 26.0.0, jsonschema 4.26.0, PyYAML 6.0.3) |
| Isolation | Fresh `git clone` and virtual environment, empty Hugging Face cache, no Hugging Face or GitHub token in the environment, and no access to the original research workspace |

Every command below was run exactly as written in the README and in
[examples.md](examples.md). Times are wall-clock times measured on this machine
and network. They are not estimates for other machines.

### Online, in README order

| Step | Command | Time | Result |
| ---: | --- | ---: | --- |
| 1 | `python3.12 -m venv .venv` | 2 s | Created |
| 2 | `python -m pip install -r requirements.lock` | 3 s | Installed |
| 3 | `python scripts/download_data.py --group listing --data-dir data` | 2 s | 2 of 19 files verified |
| 4 | `python scripts/paper_listing.py --data-dir data --output outputs/listing.csv` | under 1 s | PASS. All 984 keys, names, and counts match. |
| 5 | `python scripts/download_data.py --group engineer --data-dir data` | 5 s | 5 of 19 files verified |
| 6 | `python scripts/engineer_example.py --data-dir data --output outputs/engineer.json` | under 1 s | PASS. The search found 23 tool observations on 18 servers. |
| 7 | `python scripts/download_data.py --group researcher --data-dir data` | 41 s | 8 of 19 files verified |
| 8 | `python scripts/researcher_example.py --data-dir data --output outputs/researcher.json` | 5 s | PASS. The search found 9 pull requests in 11 stored rows. |
| 9 | `python scripts/download_data.py --group all --data-dir data` | 97 s | 19 of 19 files verified |
| 10 | `python scripts/verify_release.py --data-dir data --check` | 4 s | PASS. 19 files, 16,880,899 stored rows. |
| 11 | `python scripts/check_claims.py --data-dir data` | 64 s | PASS. 22 of 22 claims. |
| 12 | `python scripts/refresh_upstream.py` (optional) | 2 s | PASS. GitHub still matches the receipt. |

### Offline reruns

These ran with `HF_HUB_OFFLINE=1` and with `HTTP_PROXY` and `HTTPS_PROXY` set
to a closed local port, so any network request would have failed.

| Command | Result |
| --- | --- |
| `python scripts/download_data.py --group all --data-dir data --offline` | 19 of 19 files verified |
| `python scripts/paper_listing.py --data-dir data --output outputs/listing-offline.csv --check-references` | PASS. 5,138 resolved repository/server pairs, none referencing a missing record. The CSV is byte-identical to the online run. |
| `python scripts/engineer_example.py --data-dir data --output outputs/engineer-offline.json` | PASS |
| `python scripts/engineer_example.py --data-dir data --term "pull request" --output outputs/engineer-pr.json` | PASS. 36 tool observations on 5 servers. |
| `python scripts/researcher_example.py --data-dir data --output outputs/researcher-offline.json` | PASS |
| `python scripts/researcher_example.py --data-dir data --term web_search_exa --output outputs/researcher-tool.json` | PASS. 64 pull requests in 95 stored rows. |
| `python scripts/verify_release.py --data-dir data --check --group listing` | Subset of 2 files verified. The output says the complete release was not verified. |
| `python scripts/run_query.py queries/pr_storage_checks.sql --group researcher --data-dir data` | Same values as in [data-dictionary.md](data-dictionary.md#one-pull-request-several-stored-rows) |

### Unit tests

`python -m pip install -r requirements-test.lock`, then `python -m pytest`:
47 passed.

### Not tested

At the time of this local run, Linux, Windows, and the GitHub Actions
workflows had not been tested.

Publication check on 2026-10-14: the [public repository](https://github.com/khalid-tounoussi-1/mcp-eco-artifact)
and [v0.1.0 tag](https://github.com/khalid-tounoussi-1/mcp-eco-artifact/tree/v0.1.0)
are available. The [unit-test workflow on Ubuntu](https://github.com/khalid-tounoussi-1/mcp-eco-artifact/actions/runs/38488163490)
passed for commit `f6b426a`. This does not establish a full dataset reproduction
on Linux. Windows and the manual full-release workflow remain unverified here.

## Review gates

The source project requires review gates for code whose output becomes a paper
number.

- **analysis-verifier** reviewed the scripts and queries. Its first review
  found that one pull request can be stored more than once, under two `pr_id`
  values, so the researcher search listed some pull requests twice and missed
  reviews stored under the second id. It also found four minor defects. Its
  second review found the same problem across URL spellings, such as letter
  case. Its third review judged the output trustworthy for the frozen release.
  It reproduced every count in the data dictionary with independent code and
  listed four minor items, which the tested revision also fixes. Those last
  fixes were not reviewed again.
- **data-auditor** was not run. The listing and the linked-record views reuse
  queries audited before the paper. The search macros return search results,
  not reported populations.
- **challenger** was not run, because no new finding is written into the
  paper. The pull request storage counts in the data dictionary are new. They
  were derived twice, independently, but no challenger has attacked them.
