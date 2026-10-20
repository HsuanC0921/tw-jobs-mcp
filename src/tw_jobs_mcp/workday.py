"""Foreign companies that publish their jobs on Workday, filtered to Taiwan.

Workday career sites answer the same unauthenticated JSON calls their own web pages make.
One adapter covers many large semiconductor, hardware and pharma employers. The companies
below were checked to list Taiwan roles; add or remove with TW_JOBS_WORKDAY, e.g.
TW_JOBS_WORKDAY="acme.wd1/External,-micron" (tenant.wdN/site, a leading - removes).
"""
import os
import re
from concurrent.futures import ThreadPoolExecutor
from itertools import zip_longest

from . import http, text
from .boards import _CITIES, _TAIWAN
from .j104 import rank
from .j104.shape import blank_detail, blank_page, blank_row

# tenant: (data centre, career site, display name)
DEFAULT_COMPANIES = {
    "nvidia": ("wd5", "NVIDIAExternalCareerSite", "NVIDIA"),
    "amat": ("wd1", "External", "Applied Materials"),
    "analogdevices": ("wd1", "External", "Analog Devices"),
    "broadcom": ("wd1", "External_Career", "Broadcom"),
    "cadence": ("wd1", "External_Careers", "Cadence"),
    "intel": ("wd1", "External", "Intel"),
    "micron": ("wd1", "External", "Micron"),
    "marvell": ("wd1", "MarvellCareers", "Marvell"),
    "nxp": ("wd3", "careers", "NXP"),
    "kla": ("wd1", "Search", "KLA"),
    "thermofisher": ("wd5", "ThermoFisherCareers", "Thermo Fisher"),
    "hp": ("wd5", "ExternalCareerSite", "HP"),
    "hpe": ("wd5", "Jobsathpe", "HPE"),
    "salesforce": ("wd12", "External_Career_Site", "Salesforce"),
    "mastercard": ("wd1", "CorporateCareers", "Mastercard"),
    "cisco": ("wd5", "Cisco_Careers", "Cisco"),
    "logitech": ("wd5", "Logitech", "Logitech"),
    "entegris": ("wd1", "EntegrisCareers", "Entegris"),
    "philips": ("wd3", "jobs-and-careers", "Philips"),
    "gsk": ("wd5", "GSKCareers", "GSK"),
    "novartis": ("wd3", "Novartis_Careers", "Novartis"),
    "monolithicpower": ("wd12", "MPS_Careers", "Monolithic Power Systems"),
    "zeissgroup": ("wd3", "External", "ZEISS"),
    "globalfoundries": ("wd1", "external", "GlobalFoundries"),
    "flextronics": ("wd1", "Careers", "Flex"),
    "3m": ("wd1", "Search", "3M"),
    "airliquidehr": ("wd3", "AirLiquideExternalCareer", "Air Liquide"),
    "carrier": ("wd5", "jobs", "Carrier"),
    "wnc": ("wd3", "WNC_External", "WNC"),
    "stryker": ("wd1", "StrykerCareers", "Stryker"),
    "bdx": ("wd1", "external_career_site_taiwan", "BD"),
    "msd": ("wd5", "SearchJobs", "MSD"),
    "sanofi": ("wd3", "SanofiCareers", "Sanofi"),
    "citi": ("wd5", "2", "Citi"),
    "prudential": ("wd3", "prudential", "Prudential"),
    "pwc": ("wd3", "Global_Campus_Careers", "PwC"),
    "jll": ("wd1", "jllcareers", "JLL"),
    "circle": ("wd1", "circle", "Circle"),
}
PAGE = 20  # the most Workday returns per request
DEPTH = 60  # rows read per company per search; deeper pages are not reachable
_LOCATION_PARAMS = ("locationCountry", "locationHierarchy1", "locations")
_MANY = re.compile(r"(\d+)\s*(?:Locations?|個地點)", re.I)
_DAYS = re.compile(r"(\d+)")


def companies() -> dict[str, tuple[str, str, str]]:
    table = dict(DEFAULT_COMPANIES)
    for item in filter(None, (x.strip() for x in os.environ.get("TW_JOBS_WORKDAY", "").split(","))):
        if item.startswith("-"):
            table.pop(item[1:], None)
        elif m := re.fullmatch(r"([\w-]+)\.(wd\d+)/([\w-]+)", item):
            tenant, wd, site = m.groups()
            table[tenant] = (wd, site, tenant.title())
        else:
            raise http.SiteError(f"看不懂的 Workday 設定 '{item}'，格式為 tenant.wdN/site")
    return table


def _site(tenant: str) -> tuple[str, str, str, str]:
    try:
        wd, site, name = companies()[tenant]
    except KeyError:
        raise http.SiteError(f"沒有設定這家 Workday 公司：{tenant}") from None
    return f"https://{tenant}.{wd}.myworkdayjobs.com", site, name, tenant


def _api(tenant: str) -> tuple[str, str, str]:
    root, site, name, _ = _site(tenant)
    return f"{root}/wday/cxs/{tenant}/{site}", f"{root}/{site}", name


def _leaves(facets):
    for facet in facets:
        for value in facet.get("values", []):
            if "facetParameter" in value:
                yield from _leaves([value])
            elif "id" in value:
                yield facet["facetParameter"], value["id"], value["descriptor"]


def _where(facets, cities: list[str]) -> dict | None:
    """The applied-facets filter that keeps only Taiwan (or the given cities), or None."""
    found: dict[str, list[tuple[str, str]]] = {}
    for param, ident, desc in _leaves(facets):
        if _TAIWAN.search(desc):
            found.setdefault(param, []).append((ident, desc))
    if cities:
        ids = [i for i, d in found.get("locations", []) if any(c in d.lower() for c in cities)]
        return {"locations": ids} if ids else None
    for param in (*_LOCATION_PARAMS, *found):
        if found.get(param):
            return {param: [i for i, _ in found[param]]}
    return None


def _ago(label: str) -> str:
    """Workday words this in the caller's language ("Posted 3 Days Ago", "3 天前刊登")."""
    if m := _DAYS.search(label):
        return m.group(1) + ("+" if "+" in label or "超過" in label else "") + "天前"
    if re.search(r"today|今天", label, re.I):
        return "今天"
    return "昨天" if re.search(r"yesterday|昨天", label, re.I) else label.strip()


def _place(raw: dict) -> str:
    where = raw.get("locationsText", "")
    if m := _MANY.fullmatch(where):  # "3 Locations": the first one is in the path
        segment = raw["externalPath"].split("/")[2]
        return f"{' '.join(segment.replace('-', ' ').split())} 等 {m.group(1)} 地"
    return where


def _row(tenant: str, name: str, raw: dict) -> dict:
    path = raw["externalPath"].removeprefix("/job/")
    _, careers, _ = _api(tenant)
    return blank_row(
        id=f"w:{tenant}/{path}", title=raw["title"], company=name, company_id=f"w:{tenant}",
        location=_place(raw), posted=_ago(raw.get("postedOn", "")), url=f"{careers}/job/{path}")


def _list(tenant: str, body: dict) -> dict:
    api, careers, _ = _api(tenant)
    return http.post_json(f"{api}/jobs", body, referer=careers)


def _company_rows(tenant: str, keyword: str, cities: list[str], want: int) -> tuple[list[dict], int]:
    _, _, name = _api(tenant)
    base = _list(tenant, {"appliedFacets": {}, "limit": 1, "offset": 0, "searchText": ""})
    where = _where(base.get("facets", []), cities)
    if where is None:
        return [], 0
    rows, total = [], 0
    for offset in range(0, min(want, DEPTH), PAGE):
        body = {"appliedFacets": where, "limit": PAGE, "offset": offset, "searchText": keyword}
        data = _list(tenant, body)
        total = total or data.get("total", 0)
        rows += [_row(tenant, name, r) for r in data.get("jobPostings", [])]
        if len(rows) >= total:
            break
    return rows, total


def search(*, keyword: str, areas: list[str], page: int, per_page: int,
           only: str | None = None) -> tuple[dict, list[str]]:
    """(page, notes). A company that fails is skipped and named in the notes."""
    tenants = [only] if only else list(companies())
    cities = [_CITIES[c] for c in (a.replace("台", "臺")[:2] for a in areas) if c in _CITIES]
    start = (page - 1) * per_page

    def load(tenant):
        try:
            return _company_rows(tenant, keyword, cities, start + per_page), None
        except (http.SiteError, KeyError, TypeError) as exc:
            return ([], 0), f"w:{tenant}：{exc}"

    with ThreadPoolExecutor(max_workers=12) as pool:
        loaded = list(pool.map(load, tenants))
    notes = [n for _, n in loaded if n]
    total = sum(t for (_, t), _ in loaded)
    rows = [r for group in zip_longest(*(rows for (rows, _), _ in loaded)) for r in group if r]
    # Taking turns puts every company's first hit near the top, relevant or not; rank across them.
    # ponytail: the pool grows by 20 rows per company as pages deepen, so deep pages can shift a little
    if keyword:
        rows = rank.rerank(keyword, rows)
    window = rows[start:start + per_page]
    if not window and total > start:
        notes.append(f"workday 每家只讀前 {DEPTH} 筆，更深的頁數請改用關鍵字縮小範圍")
    return blank_page(window, total, page, total > start + per_page), notes


def probe(tenant: str) -> None:
    """Raise if this company's career site cannot be read or lists no Taiwan location."""
    base = _list(tenant, {"appliedFacets": {}, "limit": 1, "offset": 0, "searchText": ""})
    if _where(base.get("facets", []), []) is None:
        raise http.SiteError("目前沒有台灣地點")


def job(raw_id: str) -> dict:
    tenant, _, path = raw_id.partition("/")
    api, careers, name = _api(tenant)
    info = http.get_json(f"{api}/job/{path}", referer=careers)["jobPostingInfo"]
    places = [info.get("location", ""), *(info.get("additionalLocations") or [])]
    return blank_detail(
        id=f"w:{raw_id}", url=info.get("externalUrl") or f"{careers}/job/{path}", title=info["title"],
        company=name, company_id=f"w:{tenant}", posted=_ago(info.get("postedOn", "")),
        categories=[x for x in (info.get("timeType"), info.get("jobReqId")) if x],
        location="；".join(p for p in places if p), description=text.strip_html(info.get("jobDescription", "")),
        conditions={"headcount": "", "management": "", "business_trip": "",
                    "start": info.get("startDate", ""), "shifts": [], "hours": "", "vacation": ""})


def company(tenant: str, with_openings: bool, keyword: str = "") -> dict:
    _, careers, name = _api(tenant)
    info = {"id": f"w:{tenant}", "name": name, "industry": "", "employees": "", "capital": "", "address": "",
            "website": "", "profile": "", "products": "", "welfare": "", "followers": 0, "url": careers}
    if with_openings:
        rows, _ = _company_rows(tenant, keyword, [], PAGE * 2)
        info["openings"] = [{"id": r["id"], "title": r["title"], "salary": "待遇面議",
                             "location": r["location"], "experience": ""} for r in rows]
    return info
