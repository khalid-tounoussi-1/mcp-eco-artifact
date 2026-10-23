# Original code-release examples

These are the configuration-count and Exa examples from the original code
release v0.1.0. The current paper examples are in [examples.md](examples.md).


All commands run from the repository root, inside the environment created in
the README. Each example reads only verified local files and never contacts the
network. Outputs go to `outputs/`, which Git ignores.

## A. The paper's listing

```sh
python scripts/download_data.py --group listing --data-dir data
python scripts/paper_listing.py --data-dir data --output outputs/listing.csv
```

**Reads** `mcp_servers` and `repo_server_usage`.
**Query** [`queries/paper_listing.sql`](../queries/paper_listing.sql).
**Writes** one CSV row per candidate server with at least one matched
declaration.

The query follows Listing 1 of the paper:

1. Drop declarations whose `server_id` is null, since they matched no server.
2. Reduce declarations to distinct `(repo_id, server_id)` pairs, since one
   repository can declare a server in several files.
3. Join server names.
4. Count distinct repositories per server.

The only change from the paper is a tie-break on `server_id` after the
descending count. It fixes the order of tied rows and changes no key or count.

`configured_repositories` is the number of linked projects found in harvested
setup files. It is not an installation count, an active-user count, or a
measure of runtime use. Servers often declared under names that matched no
candidate are undercounted.

The script compares the full result, key by key, with
[`evidence/listing-expected.csv`](../evidence/listing-expected.csv). That file
holds all rows produced by the paper's listing code on the frozen release (see
[reproduction.md](reproduction.md)). Row order is not compared, because the
paper's listing leaves the order of ties open.

**Extension.** `--check-references` adds the referential checks of the dataset
card's pandas example. It confirms that every resolved pair references an
existing `consumer_repos` and `mcp_servers` record. It needs the `engineer`
group and is not part of the paper's listing.

## B. Software engineer: from a needed tool to a setup example

```sh
python scripts/download_data.py --group engineer --data-dir data
python scripts/engineer_example.py --data-dir data --output outputs/engineer.json
```

**Reads** the listing tables plus `consumer_repos`, `mcp_tools`, and
`mcp_server_transports`. **Query** [`queries/linked_tools.sql`](../queries/linked_tools.sql).

An engineer wants web search in a coding assistant.

**Part 1, search.** The script searches tool names and descriptions for
`--term` (default `web search`). It searches only tools of servers with at least
one linked consuming repository. Underscores in tool names count as spaces, so
`web search` finds `web_search_exa`. Each result shows the tool, its `source`,
its required inputs, the provider repository, the number of linked consuming
repositories, and one example setup file.

- One row per tool observation. A tool reported by both sources appears twice.
- Linked repositories are counted per server before the join, so tool rows are
  not multiplied by declarations.
- `required=None` means no stored schema. It does not mean the tool takes no
  input.
- The example setup file is the first linked declaration by consumer URL, file
  path, and `usage_id`. It is not ranked by quality.

Try another term:

```sh
python scripts/engineer_example.py --data-dir data --term "pull request" --output outputs/engineer-pr.json
```

A term with no match prints no results. The checks of Part 2 still run.

**Part 2, the paper's case.** The script then checks the case in the paper.
This case was selected deliberately from tools matching web-search names. It is
not the top search result, and the script does not pick it from the search.

| Field | Value in the frozen release |
| --- | --- |
| Tool | `web_search_exa`, `source=glama` (reported by the Glama directory) |
| Required input | `query`, a string |
| Input fields | `contextMaxCharacters`, `livecrawl`, `numResults`, `query`, `type` |
| Provider repository | https://github.com/exa-labs/exa-mcp-server |
| Consumer repository | https://github.com/mikekelly/gap |
| Setup file | `.mcp.json` |
| Declaration | command `npx`, arguments `["-y", "exa-mcp-server"]` |
| Matching method | `v1` |

Checks, each of which stops the script if it fails:

- Exactly one linked observation matches the tool, source, server, and consumer.
  Its `tool_id` and `server_id` equal the recorded ones.
- The stored schema text has the recorded SHA-256 hash and is a valid JSON
  Schema (draft 7). It accepts `{"query": "MCP documentation"}`. It rejects
  `{"numResults": 5}`, which lacks `query`, and `{"query": 5}`, which has the
  wrong type.
- Exactly one declaration links the gap project to the server in `.mcp.json`.
  Its command, arguments, and matching method equal the recorded ones exactly.
- The package `exa-mcp-server` maps to one server in `mcp_server_transports`,
  and it is the Exa server.

The JSON output keeps the identifiers, the declaration, and the tool
observations per source. A source with no rows is absent, not zero.

The declaration names a server to connect to. It does not show that the
project called this tool. No server is run, and no command from a record is
executed.

## C. Researcher: from a tool to a development discussion

```sh
python scripts/download_data.py --group researcher --data-dir data
python scripts/researcher_example.py --data-dir data --output outputs/researcher.json
```

**Reads** the engineer tables plus `server_pull_requests`,
`client_pull_requests`, and `pr_reviews`. **Query**
[`queries/server_changes.sql`](../queries/server_changes.sql).

A researcher asks how maintainers change tool inputs.

**Part 1, search.** Starting from a server (`--server-url`, default the Exa
server), the script searches its pull request titles and bodies for `--term`
(default `livecrawl`). Each result shows the pull request, its merge state,
and its review count.

- One line per pull request, identified by `pr_key` (see
  [data-dictionary.md](data-dictionary.md#one-pull-request-several-stored-rows)).
  A pull request stored more than once, under several ids, URL spellings, or
  tables, is gathered into one line that lists its `pr_id` values. The JSON
  output also lists every URL spelling.
- Reviews are gathered over all of those ids and counted by distinct
  `review_id`, before any join. If another pull request uses one of the ids,
  the output says the reviews are not attributed.
- When stored rows disagree on state or merge time, all values are shown.
- "no review rows recorded" means the release holds no review row for any of
  the ids. It does not mean the pull request had no review.

In the default search, pull requests 123 and 149 are each stored twice, once
in each pull request table under different ids. Their approving reviews sit
under the `client_pull_requests` id, so a search keyed by the server row's
`pr_id` alone would miss them.

Try another term or server:

```sh
python scripts/researcher_example.py --data-dir data --term web_search_exa --output outputs/researcher-tool.json
```

**Part 2, the paper's case.** The script checks Exa pull request 237,
https://github.com/exa-labs/exa-mcp-server/pull/237. It discusses removing
`livecrawl` from the `web_search_exa` tool schema.

- Exactly one server pull request has this URL. Its `pr_id` occurs once in
  `server_pull_requests`. Neither the URL nor the `pr_id` occurs in
  `client_pull_requests`.
- The body mentions `web_search_exa` and `livecrawl`. The pull request has a
  merge timestamp.
- Its review rows are one `COMMENTED` and one `APPROVED` review, with the
  recorded IDs.
- The frozen `pr_id` (4129324178) is the GitHub issue ID. The REST pull
  request ID is 3440544009. Numeric equality alone would not be enough to
  attribute reviews in general.
- The stored tool observation is dated 2026-06-13, after the merge on
  2026-03-24, yet its schema still lists `livecrawl`.

**Part 3, receipt replay.** [`evidence/upstream-check.json`](../evidence/upstream-check.json)
records a public GitHub inspection made on 2026-10-13. The script checks the
frozen records against it offline: the consumer's launcher and package
argument, the pull request identity, and the review IDs and states. This replay
is not a fresh GitHub check.

The tool observation and the pull request were collected at different times.
The example identifies a case to investigate. It does not establish an
interface history, present compatibility, or a current defect. An approval
does not establish tested correctness.

### Optional live refresh

```sh
python scripts/refresh_upstream.py
```

This repeats the GitHub inspection with 4 unauthenticated requests. It writes a
new file, `outputs/upstream-check-<UTC time>.json`, and reports any difference
from the frozen receipt. It never changes `evidence/upstream-check.json`, and
nothing else depends on it. It stores hashes and launcher facts, not the
inspected file.

## D. Release verification

```sh
python scripts/download_data.py --group all --data-dir data
python scripts/verify_release.py --data-dir data --check
python scripts/check_claims.py --data-dir data
```

See the README and [reproduction.md](reproduction.md).

## E. Your own query

`scripts/run_query.py` verifies the files of one download group, exposes each
table as a DuckDB view with the table's name, and prints the result of the last
statement in a SQL file. It writes nothing.

```sh
python scripts/run_query.py queries/pr_storage_checks.sql --group researcher --data-dir data
```

This query counts pull requests stored more than once, as reported in
[data-dictionary.md](data-dictionary.md#one-pull-request-several-stored-rows).
