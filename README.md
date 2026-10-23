# MCP-Eco

MCP-Eco is a dataset for studying the software behind the Model Context Protocol
(MCP). It links candidate server projects, repositories that declare them,
tool interfaces, and development records.

This repository provides scripts to download verified data, query it locally,
and reproduce the paper's examples.

[Dataset](https://huggingface.co/datasets/mcp-research-alliance/mcp-ecosystem)
· [Schema and tables](docs/data-dictionary.md)
· [Examples](docs/examples.md)
· [Reproduction](docs/reproduction.md)

## What's in the dataset?

| Area | Records |
| --- | --- |
| Server projects | Candidate repositories, registry listings, transports, dependencies |
| Interfaces | Tools and input schemas, resources, prompt templates |
| Consuming projects | Candidate repositories, discovery signals, configuration declarations |
| Development | Associated pull requests, reviews, issues, commits |

The data are released as Parquet tables with a SQL schema and collection metadata.
Use them to find tool interfaces, inspect configuration examples, or connect
interfaces to maintenance discussions.

## Quick start

Requires **Git and Python 3.12**. No API keys or database server are needed.

```sh
git clone https://github.com/khalid-tounoussi-1/mcp-eco-artifact.git
cd mcp-eco-artifact
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.lock
```

On Windows PowerShell, use `py -3.12 -m venv .venv` and
`.venv\Scripts\Activate.ps1`.

Download the GitHub example tables and inspect an issue-to-pull-request workflow:

```sh
python scripts/download_data.py --group github --data-dir data
python scripts/github_workflow.py --data-dir data --output outputs/github-workflow.json
```

An engineer wants an assistant to inspect a GitHub issue, read relevant files,
and prepare a pull request. The example retrieves the reference package's
probed `get_issue`, `get_file_contents`, and `create_pull_request` schemas.
It follows the same candidate identifier to RedisInsight's `mcp.json`
declaration of `@modelcontextprotocol/server-github`.

This is the older reference package. It is separate from
`github/github-mcp-server`. The script checks the stored schemas and package
match without running a server or executing a tool. Probe versions are not
recorded, so the link does not establish compatibility with the version in
RedisInsight's declaration.

### Choose a download

<!-- group-sizes:start -->
| Group | Tables | Parquet download | Use |
| --- | ---: | ---: | --- |
| `github` | 4 | 76,594,362 bytes | Reference GitHub tools and RedisInsight configuration |
| `arxiv` | 3 | 928,463,426 bytes | arXiv tools and a historical workflow issue |
| `listing` | 2 | 6,783,663 bytes | Older configured-repository count query |
| `engineer` | 5 | 82,924,793 bytes | Older tool search and Exa setup example |
| `researcher` | 8 | 1,697,298,748 bytes | Older Exa pull-request and review example |
| `all` | 19 | 5,309,329,895 bytes | Every released table |
<!-- group-sizes:end -->

Sizes come from the [release manifest](release/release-files.json).
The `github` and `arxiv` groups contain only their example's tables.
The older `listing`, `engineer`, and `researcher` groups remain available.
Downloads verify SHA-256 hashes and reuse existing files.
Run `python scripts/download_data.py --list` for table names.
The examples run offline after downloading.

## Create a local database

After downloading a group, save this as `create_database.py` in the repository
root and run `python create_database.py`. DuckDB is already installed.

```python
from pathlib import Path
import duckdb

Path("outputs").mkdir(exist_ok=True)
with duckdb.connect("outputs/mcp-eco.duckdb") as con:
    for path in sorted(Path("data/parquet").glob("*.parquet")):
        con.execute(
            f'CREATE OR REPLACE TABLE "{path.stem}" AS SELECT * FROM read_parquet(?)',
            [str(path)],
        )
```

Open `outputs/mcp-eco.duckdb` in a DuckDB-compatible SQL client. The script
copies every downloaded table and replaces tables with the same names on rerun.
Foreign keys are not enforced. See the [join guide](docs/data-dictionary.md)
before combining tables.

## Researcher: investigate a paper-retrieval workflow

A researcher studies coordination between tools for finding and reading papers.
The arXiv example starts with probed `search_papers`, `download_paper`, and
`read_paper` interfaces. It follows their candidate identifier to
[issue 54](https://github.com/blazickjp/arxiv-mcp-server/issues/54), which
reports asynchronous conversion interrupting a download-to-read workflow.

```sh
python scripts/download_data.py --group arxiv --data-dir data
python scripts/arxiv_workflow.py --data-dir data --output outputs/arxiv-workflow.json
```

The output includes tool schemas, the stored issue report, and their dates.
The issue closed before the probe observations. This link identifies a
historical case for study, not a reproduced failure or a defect in the probed
implementation. The data do not identify a shared implementation version.

## Run the paper's SQL query

After downloading the `github` group, run the compact query directly:

```sh
python scripts/run_query.py queries/github_workflow.sql --group github --data-dir data
```

[`queries/github_workflow.sql`](queries/github_workflow.sql) is the paper's
GitHub-interface query. [`scripts/github_workflow.py`](scripts/github_workflow.py)
adds file verification and selected-case checks. See the
[example guide](docs/examples.md) for the arXiv query and the older configuration
count and Exa examples.

## Before analysing

- Server and consumer records are **candidates**. Membership and declaration
  matches have not been fully validated.
- Configurations show **declared connections**, not installations or active use.
- `probe` capabilities were observed during collection. `glama` capabilities
  are directory-reported. Missing rows do not establish that a server has no tools.
- Records come from different times. Repository activity need not concern MCP,
  and linked records do not reconstruct an interface's version history.
- Public identities and text remain in the data. Do not use them to profile individuals.

Read the [limitations](docs/limitations.md) and [collection methods](docs/collection.md)
when designing a study.

## Reproduce the release

Downloads pin the data revision in [release/source.json](release/source.json).
The original code release is [v0.1.0](https://github.com/khalid-tounoussi-1/mcp-eco-artifact/tree/v0.1.0).
The GitHub and arXiv examples were added later on `main`.
Record the full code commit and the frozen data revision when reporting results.

```sh
python scripts/download_data.py --group all --data-dir data
python scripts/verify_release.py --data-dir data --check
python scripts/check_claims.py --data-dir data
```

These commands verify the published files and regenerate inventory claims.
See [reproduction instructions](docs/reproduction.md) for checks, tests, and
the tested environment. The original crawler is not included.

## Citation and license

If you use MCP-Eco, cite *MCP-Eco: Mining Both Sides of the Model Context
Protocol (MCP) Ecosystem* and include your data revision.
[CITATION.cff](CITATION.cff) provides the authors and preferred citation.

Code and documentation: [MIT](LICENSE).
Dataset, copied release files, schema image, and expected data records:
[CC BY 4.0](DATA-LICENSE.md). Third-party content retains its original terms.
