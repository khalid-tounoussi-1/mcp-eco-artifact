# Data license

## The dataset

The MCP-Eco dataset release,
[`mcp-research-alliance/mcp-ecosystem`](https://huggingface.co/datasets/mcp-research-alliance/mcp-ecosystem),
is licensed under [Creative Commons Attribution 4.0 International (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/).

The license covers this dataset release. It does not relicense third-party
content, such as repository code, issue and pull request text, commit messages,
or registry descriptions. That content remains under its original terms.
Respect those terms when you redistribute records.

## When the license was declared

The authors declared CC BY 4.0 on the dataset card in Hugging Face commit
`4f455810dc0a473d54845895b1be1e3657c10618` (2026-10-07). The frozen data
revision `c8edfd4bdf51b15ea95d6b0ede5dec97945f398a` predates that commit, and
its own card metadata reads `license: other`. On 2026-10-13 we compared the
file trees of the frozen revision and of `main` (commit
`3f85fee9d3c0e9518d3eae90e63ccab5844ddfca`). Only `README.md` differed. All 19
Parquet files had the same sizes and SHA-256 hashes in both.

## Personal data

`collection_metadata.json` records `scrub_pii: false`. Commit author emails,
GitHub logins, and other public identities and text can appear in the data.
The data are not anonymous. Do not use them to profile individuals.

## Files in this repository

These files are copied or derived from the dataset release and fall under the
dataset license:

- `release/source.json`, `release/release-files.json`,
  `release/collection_metadata.json`, `release/schema.sql`, `release/claims.yaml`
- `docs/schema.png`, a byte-identical copy of the release's `mcp-db.png`
- `evidence/listing-expected.csv` and `evidence/exa-expected.json`, expected
  query results over the frozen release

`evidence/upstream-check.json` records facts from a separate inspection of
public GitHub pages. It holds identifiers, hashes, titles, and review states,
not the inspected files.

The code in this repository is not covered by this file. See the Licenses
section of [README.md](README.md).
