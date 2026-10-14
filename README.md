# MCP-Eco

Find MCP tools, inspect the inputs they accept, and see how other projects
connect to their servers. You can also follow a server to its pull requests
and reviews.

These Python scripts query the [MCP-Eco dataset on Hugging Face](https://huggingface.co/datasets/mcp-research-alliance/mcp-ecosystem).
They download the data you need and run locally. You do not need a database,
Docker, or API keys.

## Start here: find a tool and a setup example

Suppose you want to add web search to a coding assistant. This example finds
matching tools, shows their required inputs, and points you to a project that
names the server in a setup file.

You need **Git and Python 3.12**. The example downloads about **83 MB** of data.

### 1. Get the code and install dependencies

```sh
git clone https://github.com/khalid-tounoussi-1/mcp-eco-artifact.git
cd mcp-eco-artifact
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.lock
```

On Windows PowerShell, create the environment with `py -3.12 -m venv .venv`
and activate it with `.venv\Scripts\Activate.ps1`.

### 2. Download the data and search

```sh
python scripts/download_data.py --group engineer --data-dir data
python scripts/engineer_example.py --data-dir data --term "web search" --output outputs/engineer.json
```

Results appear in the terminal and in `outputs/engineer.json`. They include
required inputs, the server repository, and an example project setup path.

### 3. Read the result

After the search results, the script checks the Exa example used in the paper.
This is an excerpt of that output:

```text
tool             web_search_exa (source=glama, reported by the directory)
required inputs  query
provider         https://github.com/exa-labs/exa-mcp-server
consumer         https://github.com/mikekelly/gap
setup file       .mcp.json  command=npx  args=["-y", "exa-mcp-server"]
```

The tool requires a `query` input. `source=glama` means this information came
from the Glama directory.

Open the [server repository](https://github.com/exa-labs/exa-mcp-server) for its
current setup instructions. The [project file checked for the paper](https://github.com/mikekelly/gap/blob/0e83784f1f47ab0098c2ed8595ada46852a1f89b/.mcp.json)
is a concrete example of a server declaration. It does not prove that the
project called this tool. These scripts inspect stored records and do not
start or install an MCP server.

To search for something else:

```sh
python scripts/engineer_example.py --data-dir data --term "pull request" --output outputs/pull-request-tools.json
```

The search covers tools whose servers have at least one linked project in the
dataset. It does not search every MCP tool. The fixed Exa check runs after each
search, even when you choose a different term. See the [example guide](docs/examples.md)
for the query and checks.

## Explore further

### Find pull requests about a tool input

The researcher example searches Exa's stored pull requests for `livecrawl`
and shows their merge status and recorded reviews.

**This needs about 1.70 GB of data in total.** Files downloaded for the engineer
example are reused.

```sh
python scripts/download_data.py --group researcher --data-dir data
python scripts/researcher_example.py --data-dir data --term livecrawl --output outputs/researcher.json
```

The script checks the paper's selected pull request against a saved GitHub
inspection. This is an offline check, not a fresh request. The records come
from different times and do not reconstruct an interface's version history.

See [the researcher example](docs/examples.md#c-researcher-from-a-tool-to-a-development-discussion)
for search options and how duplicate pull request records are handled.

### Run the paper's code listing

This smaller example needs about **6.8 MB**. It counts distinct projects that
name each candidate server in a harvested setup file.

```sh
python scripts/download_data.py --group listing --data-dir data
python scripts/paper_listing.py --data-dir data --output outputs/listing.csv
```

`configured_repositories` counts each project once per server. It does not
count installations or active users. The script checks every result against
the saved output of the paper's listing.

## Choose what to download

Existing files in `data/` are reused after checksum verification. The example
scripts run offline after downloading.

```sh
python scripts/download_data.py --list
```

<details>
<summary>Download sizes and included tables</summary>

Sizes are total Parquet bytes from [the release manifest](release/release-files.json).
Each group includes the tables of the group above it. Downloading also fetches
small schema and metadata files.

| Group | Files | Download | Tables added |
| --- | ---: | ---: | --- |
| `listing` | 2 | 6,783,663 bytes (6.8 MB) | `mcp_servers`, `repo_server_usage` |
| `engineer` | 5 | 82,924,793 bytes (82.9 MB) | `consumer_repos`, `mcp_tools`, `mcp_server_transports` |
| `researcher` | 8 | 1,697,298,748 bytes (1.70 GB) | `server_pull_requests`, `client_pull_requests`, `pr_reviews` |
| `all` | 19 | 5,309,329,895 bytes (5.31 GB) | every table of the release |

Add `--offline` to a download command to check local files without contacting
Hugging Face. If a file is missing or its checksum differs, the command stops
and explains the problem.

</details>

## Understand the data

- **A server record is a candidate project.** Some candidates may not be MCP
  servers. Membership has not been fully validated.
- **A setup file shows a declared connection.** It does not show that the
  server or a particular tool was used.
- **Tool sources differ.** `glama` means directory-reported information.
  `probe` means an interface observed during collection. Missing records do
  not prove that a server has no tools.
- **This is a historical dataset.** Records were collected at different times.
  Check current server documentation before using an interface.
- **The data retain public identities and text.** They are not anonymous and
  should not be used to profile individuals.

Read the [limitations](docs/limitations.md) before drawing conclusions across
the dataset.

## Reproduce the paper

The scripts pin this Hugging Face revision in
[`release/source.json`](release/source.json):

```text
c8edfd4bdf51b15ea95d6b0ede5dec97945f398a
```

The code cited by the paper is tagged [v0.1.0](https://github.com/khalid-tounoussi-1/mcp-eco-artifact/tree/v0.1.0).
The code tag and the data revision identify different things.

To check every data file and regenerate the paper's inventory, download the
full release. This requires about **5.31 GB**:

```sh
python scripts/download_data.py --group all --data-dir data
python scripts/verify_release.py --data-dir data --check
python scripts/check_claims.py --data-dir data
```

See [reproduction instructions](docs/reproduction.md) for expected results
and the tested environment. These scripts query the published data. They do
not recreate the original crawl.

## Documentation and tests

| I want to… | Read |
| --- | --- |
| Understand the tables and join keys | [Data dictionary](docs/data-dictionary.md) |
| Change a search or write my own SQL | [Example guide](docs/examples.md) |
| Understand how records were collected | [Collection methods](docs/collection.md) |
| Check the paper's results | [Reproduction instructions](docs/reproduction.md) |

To run the unit tests:

```sh
python -m pip install -r requirements-test.lock
python -m pytest
```

These tests use small synthetic records and need no data download. Checking
the actual release is a separate step described above.

## Cite MCP-Eco

Khalid Tounoussi, Mohammed Sayagh, Ali Ouni, and Yutaro Kashiwa.
*MCP-Eco: Mining Both Sides of the Model Context Protocol (MCP) Ecosystem*.
Unpublished manuscript prepared for the ICSE 2027 Tool Demonstration and Data
Showcase Track, 2026.

Please include the data revision you used. [CITATION.cff](CITATION.cff) contains
the software metadata and preferred paper citation.

<details>
<summary>BibTeX</summary>

```bibtex
@unpublished{tounoussi2026mcpeco,
  author = {Tounoussi, Khalid and Sayagh, Mohammed and Ouni, Ali and Kashiwa, Yutaro},
  title  = {{MCP-Eco}: Mining Both Sides of the {Model Context Protocol} ({MCP}) Ecosystem},
  year   = {2026},
  note   = {Unpublished manuscript prepared for the ICSE 2027 Tool Demonstration and Data Showcase Track. Associated dataset revision c8edfd4bdf51b15ea95d6b0ede5dec97945f398a},
  url    = {https://huggingface.co/datasets/mcp-research-alliance/mcp-ecosystem}
}
```

</details>

## Licenses

Code and documentation are [MIT licensed](LICENSE). The dataset is
[CC BY 4.0](DATA-LICENSE.md), with third-party content retaining its own terms.
The copied release files, schema image, and expected data records fall under
the dataset license rather than MIT.
