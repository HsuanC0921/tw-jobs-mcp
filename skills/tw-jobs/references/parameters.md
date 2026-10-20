# Parameter reference

## search_jobs

| Argument | Notes |
|---|---|
| `keyword`, `keyword_en` | Chinese for 104, English for the other sources. If only one is given, every source uses it. 1 to 3 short words each; no places, no pay. |
| `source` | `104` (default), `yourator`, `boards`, `workday`, `all` |
| `area` | Chinese place names. A bare city (`新北`) means the city; a name matching a few places (`新竹`, `中山區`) is widened to all of them, noted under the results. |
| `jobcat` | 104 job categories by Chinese name (`軟體工程師`). A name that cannot be matched becomes a keyword. `lookup_code` browses the tree. |
| `salary_min`, `salary_unit` | Floor, in the unit stated. 104 applies it on the server. Other sources ignore it and say so. |
| `education` | Postings whose requirement includes it or has none. 104 only. |
| `my_years` | The user's years of experience. 104 only. |
| `job_type` | 104 only. |
| `remote_only` | Fully or partly remote. 104 and boards. |
| `new_only` | Posted in the last 7 days. 104 only. |
| `sort` | `relevance` (default), `newest`, `salary`. A relevance search is re-ranked by how well titles and companies cover the keyword. |
| `page`, `per_page` | Up to 30 per page. |

## Other tools

- `get_job(job_id, full=false, applicants=false, similar=false)`: description is clipped at 1,500 characters unless `full=true`. 104 only: `applicants` adds who applied in the last two weeks (count inferred from 104's percentages, so read it as "at least"; education, experience, age, major, language, skills, certificates); `similar` adds up to ten similar postings with each employer's HR activity.
- `get_company(company_id, with_openings=false, keyword="", full=false)`: `keyword` lists only the matching openings. On 104 it also matches the job description, so a role whose title omits the skill is still found.
- `salary_overview(...)`: same filters as search, 104 only; groups pay by unit and reports count, min, quartiles, median, max over 1 to 5 pages.
- `lookup_code(kind, name, parent)`: find a 104 area or category code, or browse the tree. `kind` is `area` or `jobcat`.
- `sources()`: live check of which sources are reachable.

## Limits worth knowing

- 104's company-name search is blocked to scripts; reach a company through `company_id` on a posting, or put the company name in `keyword` of `search_jobs` (titles and company names are both matched).
- Workday searches read only the first 60 rows per company; narrow a deep search with a keyword.
- Yourator reports no total, so its count is a lower bound.
- Results are cached for five minutes.
