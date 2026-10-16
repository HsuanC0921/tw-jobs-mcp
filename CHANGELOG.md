# Changelog

## 1.1.1

- Published on PyPI: install and run with `uvx tw-jobs-mcp`; the README commands no longer need a GitHub URL. Package metadata (links, classifiers) added. 上架 PyPI，安裝改用 `uvx tw-jobs-mcp`。

## 1.1.0

- Agent skill: `skills/tw-jobs` teaches skill-aware agents (Claude Code, Codex and others using the Agent Skills format) to turn a plain request into precise arguments, pick a source, read the notes and report honestly. Also installable as a Claude Code plugin that bundles the server and the skill. 新增 agent skill 與 Claude Code 外掛。
- Workday now covers 38 foreign employers (was 21): Monolithic Power Systems, ZEISS, GlobalFoundries, Flex, 3M, Air Liquide, Carrier, WNC, Stryker, BD, MSD, Sanofi, Citi, Prudential, PwC, JLL and Circle join the list. Companies without a reachable Workday site (for example AMD, Synopsys, Arm) are not included. Workday 來源擴充到 38 家。
- `sources` summarizes the long list of career sites by count and names only the ones that are down.

## 1.0.0

First release. 首次發佈。

- Tools: `search_jobs`, `get_job`, `get_company`, `salary_overview`, `lookup_code`, `sources`. All read-only.
- Sources: 104, Yourator, and foreign companies' own career sites (Greenhouse, Lever, Workday), chosen with `source` or all at once with `source="all"`. Ids carry their source, and `get_job` / `get_company` route on them.
- Filters: keyword (Chinese for 104, English for the others), area, job category, salary floor, job type, remote, new postings, years of experience, education, sort, paging. A source that cannot apply a filter says so under the results.
- Built for capable models: enumerated arguments are enums in the schema, and the instructions state principles rather than examples.
- Accuracy: a ranked 104 search is reordered by how many of the query's words the title and company cover; a multi-source search ranks the merged rows the same way. On 40 searches built from real postings with partly remembered names, the intended posting ranked first 35 times (104's own order: 18).
- Empty searches loosen optional filters one at a time, then try the other sources; ambiguous place names are widened; every assumption is listed in a note.
- Compact text output, clipped long texts, and a five-minute cache keep context small; `TW_JOBS_FORMAT=json` returns full fields.
- Transports: stdio and streamable HTTP. Dockerfile and Claude Desktop `.mcpb` bundle.
- Environment: `TW_JOBS_BOARDS`, `TW_JOBS_WORKDAY` add or remove career sites.
