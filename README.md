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

Download the engineer subset and find tools for web search:

```sh
python scripts/download_data.py --group engineer --data-dir data
python scripts/engineer_example.py --data-dir data --term "web search" --output outputs/engineer.json
```

Results include tool inputs, server repositories, and linked configuration
examples. The search covers tools with linked projects and also checks the
paper's fixed Exa example. It reads stored records without running MCP servers.

### Choose a download

| Group | Use | Parquet download |
| --- | --- | ---: |
| `listing` | Count distinct configured repositories per candidate server | 6.8 MB |
| `engineer` | Find tools and configuration examples | 82.9 MB |
| `researcher` | Add pull requests and reviews | 1.70 GB |
| `all` | Get every released table | 5.31 GB |

Sizes come from the [release manifest](release/release-files.json). Groups
include the preceding groups. Downloads verify SHA-256 hashes and reuse
existing files. Run `python scripts/download_data.py --list` for table names.
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

## More examples

**Trace a tool input to a maintenance discussion:** search stored Exa pull
requests for `livecrawl` and inspect their reviews.

```sh
python scripts/download_data.py --group researcher --data-dir data
python scripts/researcher_example.py --data-dir data --term livecrawl --output outputs/researcher.json
```

**Reproduce the paper's SQL listing:** count distinct configured repositories
per candidate server.

```sh
python scripts/download_data.py --group listing --data-dir data
python scripts/paper_listing.py --data-dir data --output outputs/listing.csv
```

See the [example guide](docs/examples.md) for query details and custom SQL.

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
The paper's code release is [v0.1.0](https://github.com/khalid-tounoussi-1/mcp-eco-artifact/tree/v0.1.0).
Record both when reporting results.

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
