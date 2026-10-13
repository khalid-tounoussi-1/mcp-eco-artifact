# MCP-Eco companion code

This repository holds the code, queries, and release evidence for the MCP-Eco
dataset and its paper. It downloads the exact data release the paper uses,
reruns the paper's code listing and its two worked examples, and verifies file
identities and the release inventory. The data stay on Hugging Face. This
repository does not recreate the original crawl.

## Dataset and paper

- **Dataset.** [`mcp-research-alliance/mcp-ecosystem`](https://huggingface.co/datasets/mcp-research-alliance/mcp-ecosystem)
  on Hugging Face, frozen data revision `c8edfd4bdf51b15ea95d6b0ede5dec97945f398a`.
  Use this revision, not `main`.
- **Paper.** *MCP-Eco: Mining Both Sides of the Model Context Protocol (MCP)
  Ecosystem*, by Khalid Tounoussi, Mohammed Sayagh, Ali Ouni, and Yutaro
  Kashiwa. Unpublished manuscript prepared for the ICSE 2027 Tool Demonstration
  and Data Showcase Track. It has not been accepted or published.

## Quick start: the paper's listing

You need Python 3.12 and a 6.8 MB download. No account or token is needed.

1. Create an environment and install the pinned dependencies.

   ```sh
   python3.12 -m venv .venv
   source .venv/bin/activate
   python -m pip install -r requirements.lock
   ```

2. Download the two tables the listing reads.

   ```sh
   python scripts/download_data.py --group listing --data-dir data
   ```

3. Run the listing.

   ```sh
   python scripts/paper_listing.py --data-dir data --output outputs/listing.csv
   ```

The output starts like this:

```text
configured_repositories  server_name  (server_id)
                    469  python-sdk  (07c6bf03-21fe-573b-8584-ea198f1812dc)
                    403  run  (7b5d3922-ed37-56ac-86c3-c49b07e0a685)
                    362  Playwright MCP Server  (1ccb2319-3829-56b9-94d8-c888d656f910)
...
PASS: all 984 server_id keys, names and counts match evidence/listing-expected.csv
```

Each row is a candidate server with at least one matched declaration.
`configured_repositories` is the number of linked projects found in harvested
setup files. It counts distinct consuming
repositories with at least one configuration declaration matched to the
server. It is not an installation count, an active-user count, or a measure of
runtime use. Declarations that matched no server are excluded.

The script writes all rows to the CSV file. It then compares every key, name,
and count with `evidence/listing-expected.csv`, the full output of the original
listing in the paper. Hugging Face may warn that the requests are
unauthenticated. The dataset is public, so the warning is harmless.

## Worked examples

The two stories of the paper, each with its own download group:

```sh
python scripts/download_data.py --group engineer --data-dir data
python scripts/engineer_example.py --data-dir data --output outputs/engineer.json
python scripts/download_data.py --group researcher --data-dir data
python scripts/researcher_example.py --data-dir data --output outputs/researcher.json
```

- **Software engineer.** Search stored tool names and descriptions, inspect a
  tool's required inputs, and follow its server to a project setup file.
- **Researcher.** Start from that server, search its pull requests for a tool
  or input name, and inspect a pull request with its reviews.

Both scripts accept other search terms. Each also checks the case used in the
paper, which was selected deliberately. See [docs/examples.md](docs/examples.md).

## Download groups

Each group includes the tables of the group above it. Sizes come from
`release/release-files.json`. `python scripts/download_data.py --list` prints
them.

| Group | Files | Download | Tables added |
| --- | ---: | ---: | --- |
| `listing` | 2 | 6,783,663 bytes (6.8 MB) | `mcp_servers`, `repo_server_usage` |
| `engineer` | 5 | 82,924,793 bytes (82.9 MB) | `consumer_repos`, `mcp_tools`, `mcp_server_transports` |
| `researcher` | 8 | 1,697,298,748 bytes (1.70 GB) | `server_pull_requests`, `client_pull_requests`, `pr_reviews` |
| `all` | 19 | 5,309,329,895 bytes (5.31 GB) | every table of the release |

The downloader prints the files and their total size before it downloads.
It also fetches `collection_metadata.json` and `schema.sql` (8 KB) to confirm
the revision. Files already present are verified, never overwritten. With
`--offline` it only verifies local files and does not contact Hugging Face.
The example scripts never contact the network, so they rerun offline.

## Frozen revision and verification

`release/source.json` pins the dataset and its revision. Every script checks
the SHA-256 hashes of the three evidence files it names, then the size and
SHA-256 hash of each Parquet file, before reading any data. A missing file, a
changed manifest, or a checksum mismatch stops the script with a short message.

To verify the complete release and regenerate the paper's inventory numbers:

```sh
python scripts/download_data.py --group all --data-dir data
python scripts/verify_release.py --data-dir data --check
python scripts/check_claims.py --data-dir data
```

`verify_release.py --check` checks all 19 files and reads each table's record
count from its Parquet footer. With `--group <name>` it checks only that
group and reports that the complete release was not verified.
`check_claims.py` regenerates every number in `release/claims.yaml`.

Three identifiers are involved and they differ. The data revision is pinned
above. The code revision is the commit of this repository. The GitHub file
revision inspected for the engineer example is recorded in
`evidence/upstream-check.json`.

## Interpretation limits

- An `mcp_servers` row is a candidate server project, not a verified server.
- A configuration declaration names a server. It does not show runtime use.
- Capability rows carry a `source`. `probe` rows were observed, and `glama`
  rows were reported by a directory. A missing row is not an empty capability set.
- No semantic validation has been published, so full-cohort results are
  provisional.
- Records were acquired at different times. The export began on 2026-06-23 UTC.
- The data contain public identities and text (`scrub_pii=false`). The data
  are not anonymous. Do not use them to profile individuals.
- The worked examples are deliberately selected cases, not samples.

Details: [docs/limitations.md](docs/limitations.md).

## Documentation

- [docs/data-dictionary.md](docs/data-dictionary.md): tables, keys, nulls, units, and capability sources.
- [docs/examples.md](docs/examples.md): the listing and the two worked examples.
- [docs/collection.md](docs/collection.md): how the release was collected, as documented in the paper.
- [docs/reproduction.md](docs/reproduction.md): every paper item, its command, and a tested run.
- [docs/limitations.md](docs/limitations.md): what the data and the examples do not show.

`python scripts/run_query.py <file.sql> --group <name> --data-dir data` runs
any SQL file over verified local tables.

## Tests

```sh
python -m pip install -r requirements-test.lock
python -m pytest
```

The unit tests use synthetic records only. They check counting rules and
failure paths, need no download, and say nothing about the frozen release.
The manual workflow `.github/workflows/release-check.yml` runs every command
above on the complete release.

## Citation

Please cite the paper and name the data revision you used.

> Khalid Tounoussi, Mohammed Sayagh, Ali Ouni, and Yutaro Kashiwa. 2026.
> *MCP-Eco: Mining Both Sides of the Model Context Protocol (MCP) Ecosystem*.
> Unpublished manuscript prepared for the ICSE 2027 Tool Demonstration and Data
> Showcase Track. Dataset revision c8edfd4bdf51b15ea95d6b0ede5dec97945f398a.

```bibtex
@unpublished{tounoussi2026mcpeco,
  author = {Tounoussi, Khalid and Sayagh, Mohammed and Ouni, Ali and Kashiwa, Yutaro},
  title  = {{MCP-Eco}: Mining Both Sides of the {Model Context Protocol} ({MCP}) Ecosystem},
  year   = {2026},
  note   = {Unpublished manuscript prepared for the ICSE 2027 Tool Demonstration and Data Showcase Track. Associated dataset revision c8edfd4bdf51b15ea95d6b0ede5dec97945f398a},
  url    = {https://huggingface.co/datasets/mcp-research-alliance/mcp-ecosystem}
}
```

`CITATION.cff` describes this companion code separately and names the paper as
the preferred citation.

## Licenses

- **Dataset.** CC BY 4.0. Third-party content in the data keeps its own terms.
  See [DATA-LICENSE.md](DATA-LICENSE.md).
- **Release evidence.** `release/`, `docs/schema.png`, and the expected records
  in `evidence/` are copied or derived from the dataset release and fall under
  its license.
- **Code.** A license for the code has not been chosen yet. Until a `LICENSE`
  file is added, no license is granted for the code.
