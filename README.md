# tw-jobs-mcp

<!-- mcp-name: io.github.HsuanC0921/tw-jobs-mcp -->

**English** · [繁體中文](https://github.com/HsuanC0921/tw-jobs-mcp/blob/main/README.zh-TW.md)

[![test](https://github.com/HsuanC0921/tw-jobs-mcp/actions/workflows/test.yml/badge.svg)](https://github.com/HsuanC0921/tw-jobs-mcp/actions/workflows/test.yml)
[![PyPI](https://img.shields.io/pypi/v/tw-jobs-mcp)](https://pypi.org/project/tw-jobs-mcp/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](https://github.com/HsuanC0921/tw-jobs-mcp/blob/main/LICENSE)
![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)

Search Taiwan job postings from any AI assistant. tw-jobs-mcp is a read-only [MCP](https://modelcontextprotocol.io) server that covers **104 人力銀行**, **Yourator**, and the Taiwan openings on foreign companies' own career sites (Greenhouse, Lever, and 38 employers on Workday). Ask in plain Chinese or English; the assistant turns the request into precise filters.

No account and no API key are needed.

```bash
claude mcp add tw-jobs -s user -- uvx tw-jobs-mcp
```

> **Unofficial.** Not affiliated with or endorsed by 104 or any other site it reads. It calls the same public endpoints the sites' own pages use. Keep the request rate low and follow each site's terms. No job data ships with this project.

## What you can ask

> Find .NET backend jobs in Taipei paying at least 50,000 a month, and tell me what the market pays.

> I have two years of experience. Show remote backend postings in New Taipei, read the top three, and compare the companies.

> Is this posting worth applying to? How many people applied, and what are their backgrounds?

> Which foreign chip companies are hiring hardware engineers in Hsinchu?

> Does this company have any data roles, even ones whose title does not say so?

Behind the scenes the assistant chains the tools. The output below is illustrative; companies and ids are made up.

```text
search_jobs(keyword="後端工程師", keyword_en="backend engineer", area=["台北市"], salary_min=50000)
共 812 筆，第 1/41 頁
id|company_id|職稱|公司|薪資|地點|學歷|技能|刊登
a1b2c|x9y8z7|後端工程師 Backend Engineer|甲科技股份有限公司|月55000~80000|台北市信義區|大學~碩士|C#/.NET/MS SQL|10-18
d3e4f|w6v5u4|資深後端工程師|乙數位股份有限公司|月70000~100000|台北市內湖區|大學|Go/PostgreSQL/Docker|10-17
…

get_job("a1b2c", applicants=true)
後端工程師 Backend Engineer｜甲科技股份有限公司｜電腦軟體服務業 50人
…
HR:2 天內處理過履歷
應徵分析（近兩週）：至少 12 人（由比例推算）
學歷：大學 66.7%、碩士 33.3%
年資：1~3年 41.7%、3~5年 33.3%、無工作經驗 25%
技能：C# 58.3%、MS SQL 41.7%、Docker 25%
```

## Why this server

- **Reaches roles 104 does not have.** Foreign companies often post Taiwan openings only on their own career sites. One search with `source="all"` covers 104, Yourator, Greenhouse and Lever boards (Appier, Stripe, MongoDB, Pinkoi and more), and Workday sites of chip, hardware, pharma and finance employers (NVIDIA, Micron, Applied Materials, KLA, Cisco, Intel, NXP, GSK and more). Results from every source are merged and ranked together.
- **Finds the posting you half remember.** Results are reordered by how many of your words the title and company cover. On 40 test searches built from real postings, the intended one ranked first 35 times, against 18 with 104's own order.
- **Shows the competition.** For a 104 posting, `get_job(applicants=true)` reports how many people applied in the last two weeks and how they break down by education, experience, age, major, language, skills and certificates. Every posting shows how recently the employer handled résumés, a fair hint of whether anyone reads applications.
- **Filters that really filter.** Keyword, area, job category, salary floor (monthly, yearly, daily or hourly), years of experience, education, job type, remote, and posted in the last 7 days. Every filter was checked against the live site, and a source that cannot apply one says so under the results.
- **Made for capable models.** Every allowed value is in the schema. The server instructions state principles, not long case lists. The server handles only what the model cannot see: it widens an ambiguous place name, turns an unmatched category into a keyword, and loosens filters one at a time when nothing matches. Each of these assumptions is listed under the results.
- **Light on context.** Replies are compact tables, not JSON: 20 postings take about 2,000 characters, under a fifth of the same data as JSON. All six tool definitions together are under 3,000 characters. Long texts are clipped unless you ask for `full`.
- **Read-only and polite.** It never logs in, applies or saves anything. It paces requests to each site (one per second on 104), caches responses for five minutes, and drops the two paid postings 104 pins to every page.

## Install

Requires [uv](https://docs.astral.sh/uv/). These commands run the published package from [PyPI](https://pypi.org/project/tw-jobs-mcp/). It is also listed in the [official MCP Registry](https://registry.modelcontextprotocol.io) as `io.github.HsuanC0921/tw-jobs-mcp`.

**Claude Code**

```bash
claude mcp add tw-jobs -s user -- uvx tw-jobs-mcp
```

**OpenAI Codex CLI**

```bash
codex mcp add tw-jobs -- uvx tw-jobs-mcp
```

or in `~/.codex/config.toml`:

```toml
[mcp_servers.tw-jobs]
command = "uvx"
args = ["tw-jobs-mcp"]
startup_timeout_sec = 60   # the first run downloads dependencies
```

**Claude Desktop**: download `tw-jobs-mcp-<version>.mcpb` from [Releases](https://github.com/HsuanC0921/tw-jobs-mcp/releases) and open it, or use the JSON below.

**Gemini CLI, Cursor, Windsurf, Cline and other `mcpServers` clients**: add to `~/.gemini/settings.json`, `~/.cursor/mcp.json`, Windsurf's `mcp_config.json`, or the client's equivalent:

```json
{
  "mcpServers": {
    "tw-jobs": { "command": "uvx", "args": ["tw-jobs-mcp"] }
  }
}
```

**VS Code (GitHub Copilot)**: `.vscode/mcp.json` uses `servers` and needs a `type`:

```json
{
  "servers": {
    "tw-jobs": { "type": "stdio", "command": "uvx", "args": ["tw-jobs-mcp"] }
  }
}
```

**Remote (HTTP) and Docker**, for clients that connect by URL or a server shared by a team:

```bash
uvx tw-jobs-mcp --transport streamable-http --port 8000   # http://127.0.0.1:8000/mcp
docker build -t tw-jobs-mcp . && docker run --rm -p 8000:8000 tw-jobs-mcp
```

The HTTP server has no authentication. Keep it on localhost or a private network, or put an authenticating reverse proxy in front.

**Unreleased code**: `uvx --from git+https://github.com/HsuanC0921/tw-jobs-mcp tw-jobs-mcp`.

### Agent skill

The server already tells a model how to use it. [`skills/tw-jobs`](https://github.com/HsuanC0921/tw-jobs-mcp/blob/main/skills/tw-jobs/SKILL.md) gives agents that load skills more guidance: turning a request into arguments, picking a source, reading the notes, and reporting honestly. It follows the open Agent Skills format.

- **Claude Code**: `/plugin marketplace add HsuanC0921/tw-jobs-mcp`, then `/plugin install tw-jobs@tw-jobs-mcp` (bundles the server and the skill). Or copy `skills/tw-jobs` to `~/.claude/skills/`.
- **Codex and other skill-aware agents**: copy `skills/tw-jobs` to `~/.agents/skills/`.

## Tools

| Tool | What it does |
|---|---|
| `search_jobs` | Search postings. Returns a table: `id`, `company_id`, title, company, pay, location, education, skills, posted date. |
| `get_job` | The full posting: description, requirements, pay, hours, leave, welfare, and how recently HR handled résumés. 104 only: `applicants=true` adds the applicant count and background breakdown, `similar=true` adds similar postings. |
| `get_company` | Company profile. `with_openings=true` adds current openings; `keyword` lists only matching openings, and on 104 it also matches the job description. |
| `salary_overview` | Pay statistics (median, quartiles, min, max) over 1 to 5 pages of a 104 search, grouped by pay unit. |
| `sources` | Live check of which sources are reachable and which are blocked. |
| `lookup_code` | Find a 104 area or category code by name, or browse the tree. |

`search_jobs` arguments, all optional:

| Argument | Meaning |
|---|---|
| `keyword`, `keyword_en` | 1 to 3 short terms. Chinese in `keyword` for 104, English in `keyword_en` for the foreign sites, each a translation of the other. The assistant fills both, so a Chinese request also finds foreign postings. |
| `source` | `104` (default), `yourator`, `boards`, `workday`, or `all` |
| `area`, `jobcat` | Chinese names, e.g. `["台北市", "新北市"]`, `["軟體工程師"]` |
| `salary_min`, `salary_unit` | Salary floor and its unit: `月薪` (default), `年薪`, `日薪`, `時薪` |
| `my_years` | The user's years of experience; lists postings asking for no more |
| `education` | `高中職`, `專科`, `大學`, `碩士`, `博士` |
| `job_type` | `全職`, `兼職`, `高階`, `派遣` |
| `remote_only`, `new_only` | Remote only; posted within 7 days |
| `sort` | `relevance` (default), `newest`, `salary` |
| `page`, `per_page` | Paging, up to 30 per page |

## Sources

| `source` | Covers | Filters it applies |
|---|---|---|
| `104` | Taiwan's largest job board | all |
| `yourator` | Start-ups and foreign-company offices | `keyword`, `area`, `sort=newest` |
| `boards` | Taiwan roles on companies' Greenhouse and Lever boards | `keyword`, `area`, `remote_only` |
| `workday` | Taiwan roles at 38 foreign employers on Workday | `keyword`, `area` |
| `all` | All of the above, merged and ranked | per source; a failing source is noted, not fatal |

Ids tell where a posting lives: a bare id is 104, `y:` Yourator, `g:` / `l:` Greenhouse / Lever, `w:` Workday. Pass them back as listed.

Add or remove career sites with `TW_JOBS_BOARDS` (`g:gitlab,l:kraken,-g:stripe`) and `TW_JOBS_WORKDAY` (`acme.wd1/External,-micron`); a leading `-` removes one. Each Workday search reads the first 60 rows per company, so narrow deep searches with a keyword.

Left out on purpose: **1111** (the same kind of board as 104, smaller), **Cake** (a Cloudflare challenge on every request) and **LinkedIn** (its terms forbid automated access).

## Configuration

| Variable | Default | Meaning |
|---|---|---|
| `TW_JOBS_TRANSPORT` | `stdio` | `stdio` or `streamable-http` (same as `--transport`) |
| `TW_JOBS_HOST`, `TW_JOBS_PORT` | `127.0.0.1`, `8000` | Bind address for HTTP |
| `TW_JOBS_CACHE_TTL` | `300` | Seconds to keep responses; `0` turns the cache off |
| `TW_JOBS_BOARDS`, `TW_JOBS_WORKDAY` | built-in lists | Career sites to add or remove (see Sources) |
| `TW_JOBS_FORMAT` | `text` | `json` returns every field as compact JSON |

## How it works and its limits

104 sits behind Cloudflare, which answers ordinary HTTP clients with a 403. [`curl_cffi`](https://github.com/lexiforest/curl_cffi) presents a real Chrome TLS fingerprint and gets through. Area and category names are resolved locally against 104's public code tables.

- **Read-only.** No login, applying or bookmarking. Giving an AI your job-board password is not worth the risk.
- **No company-name search.** 104 blocks that endpoint to scripts. Reach a company through the `company_id` on a posting, or put its name in `keyword`.
- **The applicant count is inferred.** 104 publishes only percentages, so the count is the smallest number that fits them, a floor rather than an exact figure.
- `salary_overview` samples the most relevant postings rather than the whole site, and many postings do not publish pay.

## Development

```bash
uv sync
uv run pytest                  # offline unit and protocol tests
uv run pytest -m live          # against the real sites
uv run python scripts/update_codes.py   # refresh 104's area and category tables
```

## License

[MIT](https://github.com/HsuanC0921/tw-jobs-mcp/blob/main/LICENSE). Provided as is, without warranty.
