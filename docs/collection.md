# How the release was collected

This page summarizes the collection and matching stages described in the
paper. It documents them. It does not let you rerun them.

## What you can and cannot rerun

| Stage | Documented here | Rerunnable from this repository |
| --- | --- | --- |
| Discovery of candidate servers and consuming repositories | Yes | No |
| Capability probing | Yes | No. The examples never run a server. |
| Configuration parsing and server matching | Yes | No |
| Harvest of pull requests, reviews, issues, and commits | Yes | No |
| Export of the frozen release | Identity only, through `release/` | No |
| Download and verification of the frozen release | Yes | Yes, `scripts/download_data.py` and `scripts/verify_release.py` |
| The paper's listing and worked examples | Yes | Yes, see [reproduction.md](reproduction.md) |

The collector is not part of this repository. `collection_metadata.json`
records `crawler_version` 0.1.0. External registries and repositories change,
so a new crawl could not reproduce the frozen release byte for byte.

## Export

The export began on 2026-06-23 (UTC), as recorded in `collected_at_utc` of
`release/collection_metadata.json`. Records were acquired at different times
before that, so this is not a synchronized observation date. The release omits
harvest-status tables. Attempted, skipped, and failed retrievals cannot be
reconstructed from it.

## Candidate servers

The crawler discovered candidates through three channels. The
`mcp_servers.discovery_source` column records which channels surfaced each one.

- **Registries.** Adapters read the official MCP registry, Glama, Smithery,
  PulseMCP, and MCP.so. The `mcp_registries` table holds 7 seeded registry
  records. Their presence does not establish that each registry was crawled
  successfully.
- **Packages.** Searches queried npm, PyPI, Docker Hub, NuGet, crates.io, and
  Maven Central.
- **Code.** GitHub and Sourcegraph code search looked for server-authorship
  artifacts, such as `server.json` and `smithery.yaml`, and for server-side SDK
  symbols.

Repository URLs were normalized and deduplicated across channels. Each
`mcp_servers` row is therefore a candidate server project. It is not a
verified, independently deployable server. A monorepo can hold several
implementations under one URL. Package and code matches can be false
positives, such as packages whose names merely mention MCP.

Launch commands and endpoints are stored in `mcp_server_transports`. Declared
dependencies were parsed from manifests such as `package.json` and
`pyproject.toml`, fetched through the GitHub Contents API.

## Capabilities

Tools, resources, and prompts are observations tagged by `source`.

- `probe` rows come from live probing. The pipeline launched candidates that
  had a runnable transport and called `tools/list`, `resources/list`, and
  `prompts/list`. Stdio servers ran in disposable Docker containers. HTTP and
  SSE endpoints were called directly.
- `glama` rows copy capability lists published by the Glama directory.

Probing covered only candidates that could be launched or reached without
missing credentials or local setup.

## Consuming repositories

GitHub code search looked for known host configuration files, such as
`claude_desktop_config.json`, `.cursor/mcp.json`, and `.mcp.json`. Sourcegraph
also matched client SDK imports and framework adapters. Each match is kept in
`repo_discovery_signals` with a category. The `consumer_type` label summarizes
this evidence (see [data-dictionary.md](data-dictionary.md)).

## Configuration declarations

Committed configuration files were parsed into `repo_server_usage`. When a
declaration matched a candidate server, for example by package identifier or
canonical name, `server_id` was set and `match_method` records the method.
Otherwise `server_id` is null.

## Development records

Pull requests, reviews, review comments, and issues came from the GitHub REST
API, using Perceval and dedicated request handlers. Commits came from shallow
clones, read with PyDriller for diff statistics. Harvest filters differ by
table and invocation. Issue selection used update time. Stored commit
timestamps are author dates. Activity belongs to the associated repository and
need not be an MCP-specific change.

Consumer pull requests are a subset selected by coding-agent signatures.
Following the AIDev study, the pipeline matched branch names, authors, or
co-author signatures for OpenAI Codex, GitHub Copilot, Cursor, Claude Code, and
Devin. It added author matches for Google Jules and Codegen. The matched
signature is stored in `relevance_signal`.

## Validation status

File hashes and record counts of the release have been checked. Semantic
validation has not been performed. Nobody has yet measured how many candidates
are MCP servers, how accurate consumer labels are, or how often declarations
resolve to the correct server. The paper describes a planned audit. Until it is
published, full-cohort results based on MCP-Eco are provisional.
