"""The logic behind the tools. Every function returns a dict; a failure is {"error": ...}.

server.py renders these dicts as compact text for the model. Ids carry their source:
a bare id is 104, "y:" is Yourator, "g:" and "l:" are Greenhouse and Lever boards.
"""
from concurrent.futures import ThreadPoolExecutor
from itertools import chain, zip_longest

from . import boards, friendly, http, workday, yourator
from .http import SiteError
from .j104 import api, codes, query, rank, shape, stats

SOURCES = ("104", "yourator", "boards", "workday")
# Filters a source cannot apply, by the tool's own argument names.
_IGNORED = {
    "yourator": ("jobcat", "salary_min", "education", "my_years", "job_type", "remote", "new_only"),
    "boards": ("jobcat", "salary_min", "education", "my_years", "job_type", "new_only"),
    "workday": ("jobcat", "salary_min", "education", "my_years", "job_type", "remote", "new_only"),
}
_TOOL_NAME = {"remote": "remote_only"}


def _bad_name(exc: codes.AmbiguousName) -> dict:
    return {"error": str(exc), "options": [{"code": c, "name": n} for c, n in exc.options]}


def _unused(source: str, filters: dict) -> list[str]:
    return [_TOOL_NAME.get(k, k) for k in _IGNORED.get(source, ()) if filters.get(k) not in (None, False, (), [], "")]


API_ROWS = 30  # rows 104 returns per API page, two of them paid
REAL_ROWS = API_ROWS - 2


def _search_104(f: dict, per_page: int) -> dict:
    keyword = f.get("keyword") or f.get("keyword_en", "")
    f = {**f, "keyword": keyword, "keyword_en": None}
    if not keyword or f.get("sort", "relevance") != "relevance":
        return shape.search_page(api.search(query.build(**{**f, "per_page": per_page})))
    # A ranked search is cut into blocks of one API page, each reordered by how well it covers the
    # words, so the best match of a vaguely remembered name comes first.
    # ponytail: assumes 104 always pins two paid rows per page; a page with fewer drifts by a row
    start = (f.get("page", 1) - 1) * per_page
    first, last = start // REAL_ROWS, (start + per_page - 1) // REAL_ROWS
    rows, raw = [], {}
    for block in range(first, last + 1):
        raw = shape.search_page(api.search(query.build(**{**f, "page": block + 1, "per_page": API_ROWS})))
        rows += rank.rerank(keyword, raw["jobs"])
    total = max(raw["total"] - 2 * raw["pages"], len(rows))
    offset = start - first * REAL_ROWS
    return {"total": total, "page": f.get("page", 1), "pages": -(-total // per_page),
            "has_next": start + per_page < total, "jobs": rows[offset:offset + per_page]}


def _search_one(source: str, f: dict, per_page: int) -> tuple[dict, list[str]]:
    sort = f.get("sort", "relevance")
    if source == "104":
        return _search_104(f, per_page), []
    common = dict(keyword=f.get("keyword_en") or f.get("keyword", ""), areas=list(f.get("area_names") or ()), newest=sort == "newest",
                  page=f.get("page", 1), per_page=per_page)
    if source == "yourator":
        return yourator.search(**common), []
    del common["newest"]
    if source == "workday":
        return workday.search(**{k: common[k] for k in ("keyword", "areas", "page", "per_page")})
    return boards.search(**common, remote=bool(f.get("remote")))


def _run(names: tuple[str, ...], f: dict) -> dict:
    per_page = f.get("per_page", 20)
    query.check_paging(f.get("page", 1), per_page)
    if f.get("sort", "relevance") not in query.SORTS:
        raise query.ArgError(f"sort 只能是 {'、'.join(query.SORTS)}，收到 '{f['sort']}'")
    pages, notes = {}, []
    for name in names:
        try:
            pages[name], extra = _search_one(name, f, per_page)
            notes += extra
        except SiteError as exc:
            if len(names) == 1:
                raise
            notes.append(f"{name}：{exc}")
        if skipped := _unused(name, f):
            notes.append(f"{name} 未套用：{'、'.join(skipped)}")
    if not pages:
        raise SiteError("所有來源都失敗：" + "；".join(notes))
    rows = [r for r in chain.from_iterable(zip_longest(*(p["jobs"] for p in pages.values()))) if r]
    if len(pages) > 1:  # sources cannot be compared by their own scores, so rank by word coverage
        rows = rank.rerank([f.get("keyword", ""), f.get("keyword_en", "")], rows)[:per_page]
    merged = {
        "total": sum(p["total"] for p in pages.values()), "page": f.get("page", 1),
        "pages": max(p["pages"] for p in pages.values()),
        "has_next": any(p["has_next"] for p in pages.values()), "jobs": rows, "notes": notes,
        "at_least": any(p.get("at_least") for p in pages.values()),
    }
    if len(pages) > 1:
        merged["totals"] = {name: f"{p['total']}+" if p.get("at_least") else p["total"] for name, p in pages.items()}
    return merged


def _broaden(names: tuple[str, ...], f: dict, notes: list[str]) -> dict | None:
    """When nothing matched: loosen optional filters one at a time, then try the other sources."""
    if "104" in names:
        for looser, dropped in friendly.relaxations(f):
            result = _run(names, looser)
            if result["total"]:
                notes.append("原條件沒有結果，已放寬：不限" + "、".join(_TOOL_NAME.get(d, d) for d in dropped))
                return result
    if names == ("104",):
        result = _run(SOURCES[1:], f)
        if result["total"]:
            notes.append("104 沒有結果，改查其他來源")
            return result
    return None


def search_jobs(*, source: str = "104", **f) -> dict:
    f, notes = friendly.normalize(f)
    if source != "all" and source not in SOURCES:
        return {"error": f"source 只能是 {'、'.join(SOURCES)}、all，收到 '{source}'"}
    names = SOURCES if source == "all" else (source,)
    try:
        result = _run(names, f)
        if not result["total"]:
            result = _broaden(names, f, notes) or result
    except (query.ArgError, SiteError) as exc:
        return {"error": str(exc)}
    result["notes"] = notes + result["notes"]
    return result


def _route(raw: str) -> tuple[str, str]:
    if raw.startswith("y:"):
        return "yourator", raw[2:]
    if raw[:2] in ("g:", "l:"):
        return "boards", raw
    if raw.startswith("w:"):
        return "workday", raw[2:]
    return "104", raw


def get_job(job_id: str) -> dict:
    job_id = job_id.strip()
    if not job_id:
        return {"error": "job_id 不可為空，請使用 search_jobs 結果裡的 id"}
    source, raw = _route(job_id)
    try:
        if source == "yourator":
            return yourator.job(raw)
        if source == "boards":
            return boards.job(raw)
        if source == "workday":
            return workday.job(raw)
        detail = shape.job_detail(api.job(raw))
    except (SiteError, ValueError) as exc:
        return {"error": str(exc)}
    return {"id": raw, "url": f"https://www.104.com.tw/job/{raw}", **detail}


def get_company(company_id: str, with_openings: bool = False) -> dict:
    company_id = company_id.strip()
    if not company_id:
        return {"error": "company_id 不可為空，請使用搜尋結果裡的 company_id"}
    source, raw = _route(company_id)
    try:
        if source == "boards":
            return boards.company(raw, with_openings)
        if source == "workday":
            return workday.company(raw, with_openings)
        if source == "yourator":
            info = yourator.company(raw)
            if info is not None and with_openings:
                info["note"] = "Yourator 不提供職缺清單，請用 search_jobs(source=\"yourator\") 搜尋"
        else:
            info = shape.company(api.company(raw))
            if info is not None and with_openings:
                info["openings"] = shape.company_openings(api.company_jobs(raw))
    except SiteError as exc:
        return {"error": str(exc)}
    return info or {"error": f"找不到公司 '{company_id}'，請確認 company_id"}


def salary_overview(*, pages: int = 3, **filters) -> dict:
    if not 1 <= pages <= 5:
        return {"error": f"pages 必須介於 1 到 5，收到 {pages}"}
    filters, notes = friendly.normalize(filters)
    sample, total = [], 0
    try:
        for page in range(1, pages + 1):
            params = query.build(**filters, page=page, per_page=query.MAX_PAGE_SIZE)
            result = shape.search_page(api.search(params))
            sample += result["jobs"]
            total = result["total"]
            if not result["has_next"]:
                break
    except codes.AmbiguousName as exc:
        return _bad_name(exc)
    except (query.ArgError, SiteError) as exc:
        return {"error": str(exc)}
    return {"matching_jobs": total, **stats.summarize(sample), "notes": notes}


def source_status() -> dict:
    """Probe every source live, so a caller knows what is reachable right now."""
    def probe(name: str):
        try:
            if name == "104":
                api.search(query.build(per_page=1))
            elif name == "yourator":
                yourator.search(keyword="", areas=[], newest=False, page=1, per_page=1)
            elif name.startswith("w:"):
                workday.probe(name[2:])
            else:
                boards._board_rows(name)
            return name, ""
        except (SiteError, KeyError, TypeError) as exc:
            return name, str(exc) or type(exc).__name__

    http.clear_cache()  # a cached answer would hide an outage
    names = ["104", "yourator", *boards.configured(), *map("w:".__add__, workday.companies())]
    with ThreadPoolExecutor(max_workers=8) as pool:
        return {"sources": [{"name": n, "error": e} for n, e in pool.map(probe, names)]}


def lookup_code(kind: str, name: str = "", parent: str = "") -> dict:
    if kind not in codes.KINDS:
        return {"error": f"kind 只能是 {'、'.join(codes.KINDS)}，收到 '{kind}'"}
    try:
        found = codes.search(kind, name) if name.strip() else codes.children(kind, parent.strip())
    except ValueError as exc:
        return {"error": str(exc)}
    return {"matches": [{"code": c, "name": n} for c, n in found]}
