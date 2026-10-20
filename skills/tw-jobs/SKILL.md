---
name: tw-jobs
description: Search Taiwan job postings through the tw-jobs MCP server (104, Yourator, foreign companies' Greenhouse, Lever and Workday career sites). Use when the user asks in plain Chinese or English to find jobs, compare postings or companies, check salary levels, or look for foreign-company and rare roles in Taiwan. 用白話找台灣職缺、比較職缺與公司、查薪資行情、找外商或稀有缺時使用。
---

# Searching Taiwan jobs

The user describes what they want in plain words. You translate it into precise tool arguments, call the tools, and report back. The `tw-jobs` MCP server must be connected; if its tools are missing, say so and point to the install section of the README instead of guessing.

## 1. Turn the request into arguments

Read the request once and fill in every field it implies. Do not paste the user's sentence into `keyword`.

| The user says | You send |
|---|---|
| the role or skill | `keyword` (Chinese, for 104) **and** `keyword_en` (English, for the other sources): each the common title in that language, 1 to 3 short words, translated from whichever the user gave. A term with no common translation (Python, React) goes into both unchanged |
| a city or district | `area`, Chinese names: `["台北市"]`, `["新竹"]` |
| a pay floor | `salary_min` in the unit they used; set `salary_unit`: 月薪 / 年薪 / 日薪 / 時薪. Convert spoken forms: 「5 萬」→ 50000, 「年薪百萬」→ 1000000 with 年薪. 104 drops 面議 postings once a floor is set (common in finance); add `include_negotiable=true` when the user wants those too |
| years of experience | `my_years` (their own years; only roles asking for no more are listed, 經驗不拘 included) |
| remote | `remote_only=true` |
| "recent", "new" | `new_only=true` (last 7 days) or `sort="newest"` |
| a degree | `education`: 高中職 / 專科 / 大學 / 碩士 / 博士 |
| full-time, part-time… | `job_type`: 全職 / 兼職 / 高階 / 派遣 |

Leave a field out when the user did not imply it. More filters mean fewer results.

## 2. Pick the source

- **104** (default): the largest board, Chinese, and the only source that applies every filter. Use it for ordinary searches and for pay statistics (`salary_overview`).
- **all**: use whenever the user wants foreign companies, English-language roles, rare roles, or says nothing is available on 104. Merges every source and ranks them together.
- **yourator**: start-ups and foreign-company offices.
- **workday** and **boards**: foreign companies' own career sites (semiconductor, hardware, pharma, finance, and more). English titles, and only `keyword`, `area` (plus `remote_only` for boards) apply.

## 3. Search, read, then dig

1. `search_jobs`. Show the user the few best rows, not the whole table.
2. `get_job` on the two to five most promising rows; `id` goes in exactly as listed (a prefix such as `y:`, `g:`, `l:`, `w:` marks the source). The `HR` line says how recently the employer handled résumés, a fair hint of whether anyone is reading applications. For a 104 posting, add `applicants=true` when the user asks how competitive it is (applicant count and their education, experience, skills), and `similar=true` when they want more like it.
3. `get_company` with the row's `company_id` (add `with_openings=true` to see what else they hire for, or `keyword` to ask whether this company has a certain kind of role).
4. `salary_overview` to answer "what does this role pay": it samples 104 only.

## 4. Read the notes

Lines starting with `註：` under a table are assumptions the server made: ambiguous places widened, a category turned into a keyword, filters a source could not apply, optional filters loosened because nothing matched, other sources searched because 104 had nothing. **Pass these on to the user in one short sentence**, since they change what the results mean.

When a search comes back empty or far too broad, change one thing and retry: a shorter or different keyword, a different language for the keyword, a wider area, a different source. After two failed attempts, tell the user what you tried.

If a source reports it cannot be reached, call `sources` to see which are up, and carry on with the others.

## 5. Report honestly

State only what the tools returned. Never invent salary, requirements, or openings. Pay shown as 面議 means not disclosed. These tools only read postings; they cannot apply for a job or contact an employer, so hand the user the posting URL for that.

See `references/parameters.md` for argument details and limits.
