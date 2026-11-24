"""freehire.me: a public aggregator that mirrors Cake, LinkedIn, Workday, SuccessFactors, Greenhouse and
other career systems. It reads a posting from the original system, so it also shows jobs on sites that
block plain clients. Its JSON API is open, takes 100 rows a call and stops short of offset 10000.
"""
from . import http, text
from .j104.shape import blank_detail, blank_page, blank_row

_ROOT = "https://freehire.me"
PAGE_SIZE = 100
MAX_OFFSET = 9900
_TAIPEI = ("台北", "臺北", "新北", "taipei")


def _taipei_metro(areas: list[str]) -> bool:
    return any(k in a.lower() for a in areas for k in _TAIPEI)


def _row(raw: dict) -> dict:
    return blank_row(
        id=f"f:{raw['public_slug']}", title=raw.get("title", ""), company=raw.get("company", ""),
        company_id="", location=raw.get("location") or "", skills=raw.get("skills") or [],
        posted=(raw.get("posted_at") or "")[:10], url=(raw.get("url") or "").split("?")[0],
        summary=((raw.get("enrichment") or {}).get("summary") or "")[:120],
    )


def search(*, keyword: str, areas: list[str], newest: bool, page: int, per_page: int, my_years: int | None = None) -> dict:
    start = (page - 1) * per_page
    if start > MAX_OFFSET:
        return {**blank_page([], total=MAX_OFFSET + PAGE_SIZE, page=page), "at_least": True}
    params = [("countries", "tw"), ("limit", PAGE_SIZE), ("offset", start // PAGE_SIZE * PAGE_SIZE)]
    if keyword:
        params.append(("q", keyword))
    if newest:
        params.append(("sort", "posted_at"))
    if _taipei_metro(areas):
        params.append(("metros", "Taipei (TW)"))
    if my_years is not None and my_years <= 1:
        params.append(("seniority", "junior"))
    body = http.get_json(f"{_ROOT}/api/v1/jobs/search", params=params, referer=f"{_ROOT}/jobs")
    rows = body.get("data", [])
    base = start // PAGE_SIZE * PAGE_SIZE
    jobs = [_row(r) for r in rows[start - base:start - base + per_page] if r.get("public_slug")]
    total = (body.get("meta") or {}).get("total", len(rows))
    return {**blank_page(jobs, total=total, page=page, has_next=start + per_page < min(total, MAX_OFFSET + PAGE_SIZE)),
            "pages": -(-min(total, MAX_OFFSET + PAGE_SIZE) // per_page)}


def job(slug: str) -> dict:
    d = http.get_json(f"{_ROOT}/api/v1/jobs/{slug}", referer=f"{_ROOT}/jobs").get("data") or {}
    if not d:
        raise http.SiteError("找不到這個職缺")
    return blank_detail(
        id=f"f:{slug}", url=(d.get("url") or "").split("?")[0], title=d.get("title", ""),
        company=d.get("company", ""), posted=(d.get("posted_at") or "")[:10],
        location=d.get("location") or "", categories=[(d.get("enrichment") or {}).get("category", "")],
        description=text.strip_html(d.get("description", "")),
        requirements={"experience": "", "education": "", "major": [], "skills": d.get("skills") or [],
                      "languages": [], "certificates": [], "driver_license": [], "other": ""},
    )
