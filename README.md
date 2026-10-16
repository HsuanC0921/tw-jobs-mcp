# tw-jobs-mcp

**English** · [繁體中文](README.zh-TW.md)

[![test](https://github.com/HsuanC0921/tw-jobs-mcp/actions/workflows/test.yml/badge.svg)](https://github.com/HsuanC0921/tw-jobs-mcp/actions/workflows/test.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)
![MCP](https://img.shields.io/badge/MCP-stdio%20%7C%20streamable--http-green)

A read-only [Model Context Protocol](https://modelcontextprotocol.io) server for **Taiwan job boards**. It lets Claude, Codex, Gemini, Cursor and any other MCP-capable AI assistant or agent search **104 人力銀行**, **Yourator** and foreign companies' own career sites (Greenhouse, Lever, Workday) for Taiwan job postings and company profiles. More sources may be added later.

Write areas and job categories as plain Chinese names (`台北市大安區`, `軟體工程師`) and the server turns them into 104 codes. No account, no API key.

> **Unofficial.** Not affiliated with or endorsed by 104. It calls 104's public web endpoints. Keep the request rate low and follow 104's terms of use. No job data ships with this project.

## Highlights

- **Four sources that complement each other**: 104 for breadth; Yourator for start-ups and foreign-company offices; career boards (Appier, Ubiquiti, Canonical, Stripe, MongoDB, Pinkoi, Binance and more) for roles that foreign companies post on their own sites and never on 104; and Workday career sites of semiconductor, hardware and pharma employers (NVIDIA, Micron, Applied Materials, KLA, Cisco, Intel, Marvell, NXP, HP, GSK, Novartis and more). Pick one with `source`, or search them all at once with `source="all"`.
- **Six tools, all read-only**: `search_jobs`, `get_job`, `get_company`, `salary_overview`, `lookup_code`, `sources`. Every tool carries MCP read-only annotations, which clients that gate tool use can read to skip per-call confirmation.
- **Filters that really filter**: keyword, area, job category, salary floor (monthly, yearly, daily or hourly), job type, remote, posted in the last 7 days, years of experience, education. Each filter was checked against the live site.
- **Chinese names in, codes out**: ambiguous names return a list of candidates instead of a wrong guess. `lookup_code` browses the whole area and category tree level by level.
- **Built for capable models**: a user speaks plainly and the model does the translating. The schema pins every enumerated value, the server instructions state principles (what each source is, how to prepare keywords in both languages, how to convert units) instead of case lists, and the server only handles what the model cannot see: an ambiguous place name is widened to its close matches, a category that cannot be matched becomes a keyword, paging limits are clamped, and an empty search loosens its optional filters one at a time, then tries the other sources. Every assumption is listed in a note under the results.
- **Finds the posting you half remember**: a ranked 104 search is reordered by how many of your words the title and company cover, which put the intended posting first in 35 of 40 trial searches, up from 18 with 104's own order. Searching several sources ranks the merged rows the same way.
- **Chains together**: every search result carries `id` and `company_id`, so an agent can go posting → details → company without extra lookups.
- **Salary market view**: `salary_overview` summarises pay (median, quartiles, min, max) over a sample of postings, grouped by pay unit.
- **Frugal with context**: replies are compact text, not JSON. A page of 20 postings is a 20-line table of about 2,000 characters (under a fifth of the same data as compact JSON), and the six tool definitions total about 2,000 characters. Long texts are clipped unless you ask for `full`. Set `TW_JOBS_FORMAT=json` for the complete structured data.
- **Clean results**: the two paid postings 104 pins to the top of every page are always removed.
- **Polite by design**: one request per second, responses cached for five minutes.
- **Several ways to run**: stdio for local clients, streamable HTTP for remote ones, a Dockerfile and a Claude Desktop `.mcpb` bundle.

## Install

Requires [uv](https://docs.astral.sh/uv/). The commands below run the server straight from GitHub; nothing is installed permanently.

### Claude Code

```bash
claude mcp add tw-jobs -s user -- uvx --from git+https://github.com/HsuanC0921/tw-jobs-mcp tw-jobs-mcp
```

### OpenAI Codex CLI

```bash
codex mcp add tw-jobs -- uvx --from git+https://github.com/HsuanC0921/tw-jobs-mcp tw-jobs-mcp
```

or edit `~/.codex/config.toml`:

```toml
[mcp_servers.tw-jobs]
command = "uvx"
args = ["--from", "git+https://github.com/HsuanC0921/tw-jobs-mcp", "tw-jobs-mcp"]
startup_timeout_sec = 60   # the first run downloads dependencies
```

### Claude Desktop

Download `tw-jobs-mcp-<version>.mcpb` from [Releases](https://github.com/HsuanC0921/tw-jobs-mcp/releases) and open it, or add the JSON below to `claude_desktop_config.json`.

### Gemini CLI, Cursor, Windsurf, Cline and other `mcpServers` clients

Add to `~/.gemini/settings.json`, `~/.cursor/mcp.json` (or `.cursor/mcp.json`), Windsurf's `mcp_config.json`, or the client's equivalent:

```json
{
  "mcpServers": {
    "tw-jobs": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/HsuanC0921/tw-jobs-mcp", "tw-jobs-mcp"]
    }
  }
}
```

### VS Code (GitHub Copilot)

`.vscode/mcp.json` uses `servers` and needs a `type`:

```json
{
  "servers": {
    "tw-jobs": {
      "type": "stdio",
      "command": "uvx",
      "args": ["--from", "git+https://github.com/HsuanC0921/tw-jobs-mcp", "tw-jobs-mcp"]
    }
  }
}
```

### Remote (HTTP) and Docker

Clients that connect by URL, or a server shared inside a team:

```bash
uvx --from git+https://github.com/HsuanC0921/tw-jobs-mcp tw-jobs-mcp --transport streamable-http --port 8000
# endpoint: http://127.0.0.1:8000/mcp
```

```bash
docker build -t tw-jobs-mcp .
docker run --rm -p 8000:8000 tw-jobs-mcp
```

```bash
claude mcp add --transport http tw-jobs http://127.0.0.1:8000/mcp
codex mcp add tw-jobs --url http://127.0.0.1:8000/mcp
```

The HTTP server has no authentication. Keep it on localhost or a private network, or put an authenticating reverse proxy in front of it.

### From a clone

```bash
git clone https://github.com/HsuanC0921/tw-jobs-mcp
cd tw-jobs-mcp
claude mcp add tw-jobs -- uv run --project "$PWD" tw-jobs-mcp
```

## Agent skill

The server already tells a model how to use it. The skill in [`skills/tw-jobs`](skills/tw-jobs/SKILL.md) goes further for agents that load skills: how to turn a plain request into arguments, which source to pick, how to read the notes, and what to report. It follows the open Agent Skills format.

- **Claude Code**: install the plugin, which bundles the server and the skill: `/plugin marketplace add HsuanC0921/tw-jobs-mcp`, then `/plugin install tw-jobs@tw-jobs-mcp`. Or copy `skills/tw-jobs` to `~/.claude/skills/`.
- **Codex and other skill-aware agents**: copy `skills/tw-jobs` to `~/.agents/skills/` (or `.agents/skills/` in a repository).

## Tools

| Tool | What it does |
|---|---|
| `search_jobs` | Search postings. Returns a table: `id`, `company_id`, title, company, pay, location, education, skills, posted date. |
| `get_job` | Full posting: description, requirements, skills, salary, working hours, vacation, business trip, welfare. The description is clipped at 1,500 characters unless `full=true`. |
| `get_company` | Company profile; `with_openings=true` adds its current openings; `full=true` lifts the clipping. |
| `salary_overview` | Pay statistics over the first 1 to 5 pages (30 postings each) of a search, grouped by pay unit. |
| `sources` | Live check of which sources (104, Yourator, each career board) are reachable right now and which are blocked. |
| `lookup_code` | Find an area or category code by name, or browse the tree with `parent`. |

`search_jobs` arguments (all optional):

| Argument | Meaning |
|---|---|
| `keyword`, `keyword_en` | Search words: 1 to 3 short terms. `keyword` is Chinese for 104, `keyword_en` English for the other sources (foreign sites list English titles). The AI fills both, each translating the other, so a Chinese request finds foreign postings and an English one finds 104 postings; users never see them |
| `area`, `jobcat` | Lists of Chinese names, e.g. `["台北市", "新北市"]`, `["軟體工程師"]` |
| `salary_min`, `salary_unit` | Salary floor and its unit: `月薪` (default), `年薪`, `日薪`, `時薪`. A server-side filter |
| `education` | `高中職`, `專科`, `大學`, `碩士`, `博士`: postings whose education requirement includes it (or has none) |
| `my_years` | Your years of experience: only postings asking for no more than that |
| `job_type` | `全職`, `兼職`, `高階`, `派遣` |
| `remote_only` | Fully or partly remote only |
| `new_only` | Posted within 7 days |
| `sort` | `relevance` (default), `newest`, `salary` |
| `page`, `per_page` | Paging, up to 30 per page |

### Sources

`source` picks where to search. Result ids say where a posting lives, and `get_job` / `get_company` route on them: a bare id is 104, `y:` is Yourator, `g:` and `l:` are Greenhouse and Lever boards, `w:` is Workday. Pass ids back exactly as listed.

| `source` | Covers | Filters it applies |
|---|---|---|
| `104` (default) | Taiwan's largest board | all of them |
| `yourator` | Start-ups, foreign-company offices | `keyword`, `area`, `sort=newest` |
| `boards` | Taiwan roles on companies' own Greenhouse / Lever boards | `keyword`, `area`, `remote_only` |
| `workday` | Taiwan roles at 38 foreign employers on Workday, from chips and hardware to pharma and finance | `keyword`, `area` |
| `all` | The four above, interleaved | per source; a failing source is reported, not fatal |

Filters a source cannot apply are named in a `註：…未套用` line under the table, so nothing is silently ignored. `salary_overview` and `lookup_code` are 104-only.

Add boards with `TW_JOBS_BOARDS`, e.g. `g:gitlab,l:kraken,-g:stripe` (`g:` Greenhouse, `l:` Lever, a leading `-` removes one). A board without Taiwan roles simply returns nothing.

`TW_JOBS_WORKDAY` does the same for Workday: `acme.wd1/External,-micron` (`tenant.wdN/site`, a leading `-` removes). Each Workday search reads only the first 60 rows per company, so narrow deep searches with a keyword. These are the same unauthenticated calls the companies' own career pages make; check each company's terms before heavy use.

Left out on purpose: **1111** (same kind of board as 104, smaller), **Cake** (Cloudflare challenge on every request) and **LinkedIn** (its terms prohibit automated access).

## Examples

> Find .NET backend jobs in Taipei paying at least 50,000 a month, and tell me what the market pays.

> I have two years of experience. Show remote backend postings in New Taipei, read the top three, and compare the companies.

```text
search_jobs(keyword="後端工程師", area=["台北市"])
共 1716 筆，第 1/86 頁
id|company_id|職稱|公司|薪資|地點|學歷|技能|刊登
8mve7|1a2x6bmz67|後端工程師|途銳資訊股份有限公司|月45000~70000|台北市南港區|專科~碩士|PHP/MySQL/AWS/Linux/Git|10-02
…
```

## Configuration

| Variable | Default | Meaning |
|---|---|---|
| `TW_JOBS_TRANSPORT` | `stdio` | `stdio` or `streamable-http` (same as `--transport`) |
| `TW_JOBS_HOST`, `TW_JOBS_PORT` | `127.0.0.1`, `8000` | Bind address for the HTTP transports |
| `TW_JOBS_CACHE_TTL` | `300` | Seconds to keep responses; `0` turns the cache off |
| `TW_JOBS_BOARDS` | built-in list | Extra career boards, comma separated (see Sources) |
| `TW_JOBS_WORKDAY` | built-in list | Extra Workday sites, `tenant.wdN/site` (see Sources) |
| `TW_JOBS_FORMAT` | `text` | `json` returns every field as compact JSON instead of the text tables |

## How it works

104 sits behind Cloudflare, which answers ordinary HTTP clients with a 403. [`curl_cffi`](https://github.com/lexiforest/curl_cffi) sends the TLS fingerprint of a real Chrome instead, which gets through. Area and category names are resolved locally against 104's public code tables (`src/tw_jobs_mcp/j104/data/`).

## Limits, on purpose

- **Read-only.** No login, applying or bookmarking. Handing an AI your job-board password is not worth the risk.
- **No company-name search.** 104 puts a Cloudflare challenge in front of that endpoint. Reach companies through the `company_id` on postings.
- `salary_overview` is a sample of the most relevant postings, not a census, and many postings do not publish pay (`undisclosed_share`).

## Development

```bash
uv sync
uv run pytest                  # offline: unit tests plus stdio and HTTP protocol tests
uv run pytest -m live          # against the real 104 site
uv run python scripts/update_codes.py   # refresh the area and category tables
```

## License

[MIT](LICENSE). Provided as is, without warranty.
