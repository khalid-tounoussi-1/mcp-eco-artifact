# Limitations

## Of the data

**Coverage.** MCP-Eco is a snapshot of a changing ecosystem. Coverage depends on
the sources queried and their search limits. It is not exhaustive. Record counts
describe this release, not the MCP population. Directory metadata can be stale
or wrong. The release omits harvest-status tables, so attempted, skipped, and
failed retrievals cannot be reconstructed.

**Timing.** The export began on 2026-06-23 (UTC). Records were acquired at
different times before that. Star counts were recorded at discovery time and
are not a synchronized snapshot. Flag them wherever they filter or correlate.

**Candidate servers.** An `mcp_servers` row is a claim that a project is an MCP
server, not a fact. The table can include false positives and monorepos with
several implementations.

**Capabilities.** Probing covers only candidates that could be launched or
reached. A candidate without `probe` rows was not probed, failed to start, or
returned nothing. The release does not distinguish these cases. Do not fill
missing rows with zero. Keep `probe` (observed) and `glama` (reported) rows
apart.

**Consumers and declarations.** Consumer labels rest on code-search signals.
A signal shows that a repository references MCP, not that it uses MCP.
Unmatched declarations can hide real links, and matched ones can be wrong. A
declaration names a server to connect to. It does not show that a project ran
the server or called a tool.

**Development records.** Activity belongs to the associated repository and
need not concern MCP. Bot flags and agent signatures can miss or misattribute
contributions. Consumer pull requests are a signature-matched subset. One pull
request can be stored more than once, under different `pr_id` values or URL
spellings, in one table or across both. Count pull requests by `pr_key` and
gather reviews as described in [data-dictionary.md](data-dictionary.md).
Pull requests of a renamed repository can appear under both names.

**Validation.** File identities and record counts have been checked. No
semantic validation has been published. Full-cohort results are provisional.

## Of the worked examples

- The Exa case was selected deliberately from tools matching web-search names
  and then checked individually. It is not a sample. It supports no estimate of
  coverage, prevalence, or correctness.
- A search match is a text match, not a classification of a tool or a pull
  request.
- Schema validation checks stored metadata. No MCP server was run and no tool
  was called.
- The stored tool schema and the pull request were collected at different
  times. The stored schema still contains `livecrawl`, although it was
  collected after the pull request that discusses removing `livecrawl` merged.
  The declaration does not pin a package version. These records cannot show
  which interface the consuming project encountered. They are not a
  before-and-after interface history and do not show a current defect.
- An approving review does not establish tested correctness. The recorded
  approval in the example has no substantive feedback text.
- `evidence/upstream-check.json` records a public GitHub inspection made on
  2026-10-13. It pins the consumer file revision inspected then, which is not
  the originally harvested revision. Replaying it offline is not a fresh check.

## Of this repository

- It verifies and queries the frozen release. It does not include or rerun the
  collector.
- A unit-test pass in CI uses synthetic records only. It says nothing about
  the frozen release. Only the commands in [reproduction.md](reproduction.md),
  run on downloaded files, check the release.

## Ethics and redistribution

Records were collected from public registries, public code search, and public
repositories. The release metadata records `scrub_pii=false`. Commit author
emails, GitHub identities, and public text such as issue and pull request
bodies can remain in the data. The data are not anonymous. Do not use them to
profile individuals. CC BY 4.0 covers the dataset release and does not
relicense third-party content.
