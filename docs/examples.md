# Examples

These purposefully selected cases illustrate joins in the frozen release.
They are not population samples. Download commands contact Hugging Face.
The example scripts and SQL then read verified local files offline.
Nothing runs an MCP server or executes a command found in a record.

## Software engineer: GitHub tools and a project setup

An engineer wants an assistant to inspect an issue, read source files, and
prepare a pull request. MCP-Eco provides the recorded input schemas of the
reference GitHub package and an existing project's configuration to inspect.

```sh
python scripts/download_data.py --group github --data-dir data
python scripts/github_workflow.py --data-dir data --output outputs/github-workflow.json
```

The script reads `mcp_server_transports`, `mcp_tools`, `repo_server_usage`, and
`consumer_repos`. The selection is explicit in
[`queries/github_workflow.sql`](../queries/github_workflow.sql).

- Resolve `@modelcontextprotocol/server-github` to its candidate identifier.
- Keep probed `get_issue`, `get_file_contents`, and `create_pull_request` tools.
- Follow that identifier to RedisInsight's root `mcp.json` declaration.
- Keep package-identifier matches and check the actual launcher and arguments.

The declaration uses `npx` with
`["-y", "@modelcontextprotocol/server-github@2025.4.8"]`, labeled
`package_ver`. An independent public setup example is the
[pinned RedisInsight file](https://github.com/redis/RedisInsight/blob/f0c887c73011afdd5e3fb03f9bb341d915eec378/mcp.json).
That public revision does not identify the commit used during collection.

The JSON output includes complete input schemas and the configuration entry.
The checks compare schemas with recorded evidence, accept illustrative valid
inputs, and reject missing inputs and a wrong input type. The package mapping
and setup fields must match the selected records.

This is the older reference package, separate from `github/github-mcp-server`.
The stored reference URL contains `/tree/head/` and is not a working public
link. Package identity is used for this case. Probe records do not record a
package version, so the example does not establish compatibility with the
version RedisInsight declares or show that RedisInsight called these tools.

### Compact paper query

```sh
python scripts/run_query.py queries/github_workflow.sql --group github --data-dir data
```

Each result pairs a selected tool with the same setup declaration. Repeated
configuration fields are intentional. This query does not count distinct
servers or projects. The full Python script adds identity and schema checks.

## Researcher: arXiv tools and a historical issue

A researcher studies coordination between paper-retrieval tools. Starting
from the probed interfaces of `blazickjp/arxiv-mcp-server`, the example connects
`search_papers`, `download_paper`, and `read_paper` to a development report.

```sh
python scripts/download_data.py --group arxiv --data-dir data
python scripts/arxiv_workflow.py --data-dir data --output outputs/arxiv-workflow.json
```

The script reads `mcp_servers`, `mcp_tools`, and `ecosystem_issues`.
[`queries/arxiv_workflow.sql`](../queries/arxiv_workflow.sql) defines separate
tool and issue views joined through `server_id`.

[Issue 54](https://github.com/blazickjp/arxiv-mcp-server/issues/54) reports that
asynchronous conversion interrupted a sequential download-to-read workflow.
This provides a case for investigating tool coordination and interface design.
The JSON output retains tool descriptions, schemas, observation dates, the
stored issue body, and issue dates. Checks require the selected tool and issue
identities, the recorded schemas and issue-text hash, and the expected timing.

The issue closed before the later probe observations. The observed download
description says content is returned directly, while the issue reports older
asynchronous behavior. The shared repository identifier does not establish a
common implementation version, an interface history, or a defect in the
probed implementation. These scripts do not reproduce the reported failure.

To inspect the repository-level join directly:

```sh
python scripts/run_query.py queries/arxiv_workflow.sql --group arxiv --data-dir data
```

The same issue appears beside each selected tool. Treat it as one historical
report associated with the server, not as independent reports for each tool.

## Evidence, other queries, and release verification

[`evidence/github-arxiv-expected.json`](../evidence/github-arxiv-expected.json)
records the selected identities, schemas, configuration fields, and issue hash.
Input files are verified against the frozen release manifest before querying.
These checks verify the stored cases, not candidate membership across the
release or the correctness of all configuration matches.

The [original code-release examples](legacy-examples.md) remain available,
including the configuration count, Exa tool search, and pull-request review
queries. They retain their existing commands and tests.

See [reproduction.md](reproduction.md) for release verification and the record
of checks. [`scripts/run_query.py`](../scripts/run_query.py) also supports custom
SQL over any named download group.
