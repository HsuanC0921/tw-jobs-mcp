"""Cake (cake.me, formerly CakeResume): Taiwan start-ups, foreign offices and many local firms.

Its search API lives on api.cake.me, which does not sit behind the Cloudflare challenge that
guards www.cake.me, so a plain client reaches it. The API takes 50 rows a page and stops at page 10,
so one query reaches at most 500 postings; narrow with area, my_years or a sharper keyword.
"""
import re

from . import http, text
from .j104.shape import blank_detail, blank_page, blank_row

_API = "https://api.cake.me/api/client"
_WEB = "https://www.cake.me"
PAGE_SIZE = 50  # the API rejects anything larger
MAX_PAGES = 10
_REFERER = f"{_WEB}/"
# year_of_seniority bucket -> years the posting asks for at least
_BUCKETS = {"0_1": 0, "1_3": 1, "3_5": 3, "5_10": 5}
_UNITS = {"per_month": "月薪", "per_year": "年薪", "per_day": "日薪", "per_hour": "時薪"}
_REMOTE = {"no_remote_work": "", "partial_remote_work": "部分遠端", "full_remote_work": "完全遠端"}
_ID = re.compile(r"^([^/]+)/(.+)$")


def _headers_note() -> dict:
    return {"Origin": _WEB}


def city_names(areas: list[str]) -> list[str]:
    """Cake location strings for city-level names; districts and unknown names are skipped."""
    out = []
    for name in areas:
        name = name.replace("臺", "台")
        if name.endswith(("市", "縣")) and len(name) >= 3:
            out.append(f"{name}, 台灣")
        elif len(name) == 2:  # 新北、台北、高雄: a bare city without its suffix
            out.append(f"{name}市, 台灣")
    return list(dict.fromkeys(out))


def _seniority(my_years: int | None) -> list[str]:
    if my_years is None:
        return []
    return [bucket for bucket, floor in _BUCKETS.items() if floor <= my_years]


def _pay(salary: dict | None) -> dict | None:
    if not salary:
        return None
    unit = _UNITS.get(salary.get("type") or "")
    low, high = (int(float(salary.get(k) or 0)) or None for k in ("min", "max"))
    if not unit or not (low or high):
        return None
    return {"unit": unit, "min": low, "max": high}


def _salary_label(pay: dict | None) -> str:
    if not pay:
        return ""
    low, high = pay["min"], pay["max"]
    span = f"{low:,}~{high:,}" if low and high else f"{(low or high):,}"
    return f"{pay['unit']}{span}"


def _row(raw: dict) -> dict:
    company = raw.get("page") or {}
    cpath, path = company.get("path", ""), raw["path"]
    pay = _pay(raw.get("salary"))
    return blank_row(
        id=f"c:{cpath}/{path}", title=raw["title"], company=company.get("name", ""),
        company_id=f"c:{cpath}", salary=_salary_label(pay), pay=pay,
        location="、".join((raw.get("locations") or [])[:2]), skills=raw.get("tags") or [],
        posted=(raw.get("content_updated_at") or "")[:10], url=f"{_WEB}/companies/{cpath}/jobs/{path}",
        summary=text.strip_html(raw.get("description", ""))[:120],
    )


def search(*, keyword: str, areas: list[str], page: int, per_page: int, my_years: int | None = None,
           remote: bool = False) -> dict:
    start = (page - 1) * per_page
    if start >= PAGE_SIZE * MAX_PAGES:
        return {**blank_page([], total=PAGE_SIZE * MAX_PAGES, page=page), "at_least": True}
    first, last = start // PAGE_SIZE + 1, min((start + per_page - 1) // PAGE_SIZE + 1, MAX_PAGES)
    filters = {"job_source": ["cake", "external"]}
    if cities := city_names(areas):
        filters["locations"] = cities
    if buckets := _seniority(my_years):
        filters["year_of_seniority"] = buckets
    if remote:
        filters["remote"] = ["partial_remote_work", "full_remote_work"]
    rows, total = [], 0
    for number in range(first, last + 1):
        body = http.post_json(f"{_API}/v2/jobs/search", {
            "query": keyword, "filters": filters, "sort_by": "latest", "page": number, "per_page": PAGE_SIZE,
        }, referer=_REFERER, headers=_headers_note())
        rows += [r for r in body.get("data", []) if r.get("path") and r.get("title")]
        total = body.get("total_entries") or 0
        if number >= (body.get("total_pages") or 1):
            break
    offset = start - (first - 1) * PAGE_SIZE
    jobs = [_row(r) for r in rows[offset:offset + per_page]]
    has_next = start + per_page < min(total, PAGE_SIZE * MAX_PAGES)
    return {**blank_page(jobs, total=total, page=page, has_next=has_next), "pages": -(-min(total, PAGE_SIZE * MAX_PAGES) // per_page)}


def job(raw_id: str) -> dict:
    m = _ID.match(raw_id)
    if not m:
        raise http.SiteError("Cake 職缺編號應為 c:公司/職缺")
    cpath, path = m.groups()
    d = http.get_json(f"{_API}/v1/jobs/{path}", referer=_REFERER, headers=_headers_note())
    pay = _pay({"min": d.get("salary_min"), "max": d.get("salary_max"), "type": d.get("salary_type")})
    levels = {"entry_level": "入門", "mid_senior_level": "中高階", "associate": "初階", "director": "主管", "internship_level": "實習"}
    where = d.get("locations") or ""
    if isinstance(where, list):
        where = [w.get("full_name", "") if isinstance(w, dict) else w for w in where]
    return blank_detail(
        id=f"c:{cpath}/{path}", url=f"{_WEB}/companies/{d.get('page_path') or cpath}/jobs/{path}",
        title=d.get("title", ""), company_id=f"c:{d.get('page_path') or cpath}", salary=_salary_label(pay),
        posted=(d.get("content_updated_at") or "")[:10],
        categories=[levels.get(d.get("seniority_level") or "", ""), d.get("job_type") or ""],
        location=where if isinstance(where, str) else "、".join(where),
        remote=_REMOTE.get(d.get("remote") or "", ""),
        description=text.strip_html(d.get("description", "")),
        requirements={"experience": str(d.get("min_work_exp_year", "")) and f"{d.get('min_work_exp_year')} 年以上",
                      "education": "", "major": [], "skills": d.get("tags") or [], "languages": [],
                      "certificates": [], "driver_license": [],
                      "other": text.strip_html(d.get("requirements", ""))},
        welfare=("面試流程：" + text.strip_html(d["interview_process"])) if d.get("interview_process") else "",
    )


def company(path: str) -> dict | None:
    d = http.get_json(f"{_API}/v1/pages/{path}", referer=_REFERER, headers=_headers_note())
    if not d.get("name"):
        return None
    return {"id": f"c:{path}", "name": d["name"], "industry": "", "employees": "", "capital": "",
            "address": d.get("address") or "", "website": d.get("recruiting_website_url") or "",
            "profile": text.strip_html(d.get("description", "")),
            "products": text.strip_html(d.get("products_or_services", "")),
            "welfare": text.strip_html(d.get("employee_benefits", "")), "followers": 0,
            "url": f"{_WEB}/companies/{path}"}
