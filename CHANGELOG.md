# Changelog

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
