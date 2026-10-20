"""Yourator: Taiwan start-ups and foreign-company offices, a good complement to 104.

The listing comes from Yourator's own JSON API; a posting's details come from the
schema.org block its page publishes for search engines.
"""
import re

from . import http, text
from .j104.shape import blank_detail, blank_page, blank_row

_ROOT = "https://www.yourator.co"
PAGE_SIZE = 20  # fixed by the site
_AREAS = {"臺北市": "TPE", "新北市": "NWT", "桃園市": "TAO", "新竹市": "HSZ", "新竹縣": "HSQ",
          "臺中市": "TXG", "嘉義市": "CYI", "臺南市": "TNN", "高雄市": "KHH", "雲林縣": "YUN"}
_KINDS = {"FULL_TIME": "全職", "PART_TIME": "兼職", "CONTRACTOR": "接案", "INTERN": "實習", "TEMPORARY": "短期"}
_PAY = re.compile(r"NT\$\s*([\d,]*)\s*-\s*([\d,]*)\s*\((月薪|年薪|日薪|時薪)\)")
_PATH = re.compile(r"/companies/([^/]+)/jobs/(\d+)")


def area_codes(names: list[str]) -> list[str]:
    """Yourator area codes for Chinese place names (a district counts as its city)."""
    names = [n.replace("台", "臺") for n in names]
    # "新竹縣" is one city; a bare "新竹" covers both 新竹市 and 新竹縣
    return [code for city, code in _AREAS.items()
            if any(city == n[:3] or (len(n) < 3 or n[2] not in "市縣") and city[:2] == n[:2] for n in names)]


def _pay(label: str) -> dict | None:
    m = _PAY.search(label or "")
    if not m:
        return None
    low, high = (int(g.replace(",", "")) if g else None for g in m.groups()[:2])
    return {"unit": m.group(3), "min": low, "max": high}


def _row(raw: dict) -> dict:
    slug, number = _PATH.search(raw.get("path", "")).groups()
    return blank_row(
        id=f"y:{slug}/{number}", title=raw["name"], company=(raw.get("company") or {}).get("brand", ""),
        company_id=f"y:{slug}", salary=raw.get("salary", ""), pay=_pay(raw.get("salary", "")),
        location=raw.get("location") or "", skills=raw.get("tags") or [],
        posted=raw.get("lastActiveAt", ""), url=f"{_ROOT}{raw['path']}",
    )


def search(*, keyword: str, areas: list[str], newest: bool, page: int, per_page: int) -> dict:
    start = (page - 1) * per_page
    first, last = start // PAGE_SIZE + 1, (start + per_page - 1) // PAGE_SIZE + 1
    filters = [("term[]", keyword)] if keyword else []
    filters += [("area[]", code) for code in area_codes(areas)]
    if newest:
        filters.append(("sort", "recent_updated"))
    rows, more = [], False
    for number in range(first, last + 1):
        payload = http.get_json(f"{_ROOT}/api/v4/jobs", params=[("page", number), *filters],
                                referer=f"{_ROOT}/jobs")["payload"]
        rows += payload["jobs"]
        more = bool(payload["hasMore"])
        if not more:
            break
    offset = start - (first - 1) * PAGE_SIZE
    jobs = [_row(j) for j in rows[offset:offset + per_page]]
    has_next = more or len(rows) > offset + per_page
    # the site reports no total, so this is a lower bound
    found = blank_page(jobs, total=start + len(jobs), page=page, has_next=has_next)
    return {**found, "at_least": has_next}


def job(raw_id: str) -> dict:
    slug, number = raw_id.split("/", 1)
    url = f"{_ROOT}/companies/{slug}/jobs/{number}"
    ld = text.json_ld(http.get_text(url), "JobPosting")
    if not ld:
        raise http.SiteError("找不到這個職缺")
    org = ld.get("hiringOrganization") or {}
    place = ((ld.get("jobLocation") or {}).get("address")) or {}
    closes = str(ld.get("validThrough", ""))
    return blank_detail(
        id=f"y:{raw_id}", url=url, title=ld.get("title", ""), company=org.get("name", ""),
        company_id=f"y:{slug}", posted=str(ld.get("datePosted", ""))[:10],
        closes="" if closes.startswith("21") else closes,  # 21xx means "no deadline"
        categories=[_KINDS.get(ld.get("employmentType"), "")] if ld.get("employmentType") else [],
        location=place.get("addressLocality", "") + place.get("streetAddress", ""),
        description=text.strip_html(ld.get("description", "")),
    )


def company(raw_id: str) -> dict | None:
    page = http.get_text(f"{_ROOT}/companies/{raw_id}")
    org = text.json_ld(page, "Organization")
    if not org:
        return None
    address = org.get("address") or {}
    return {"id": f"y:{raw_id}", "name": org.get("name", ""), "industry": "", "employees": "",
            "capital": "", "address": address.get("addressLocality", "") + address.get("streetAddress", ""),
            "website": (org.get("sameAs") or [""])[0] if isinstance(org.get("sameAs"), list) else org.get("sameAs", ""),
            "profile": text.strip_html(org.get("description", "")), "products": "", "welfare": "",
            "followers": 0, "url": f"{_ROOT}/companies/{raw_id}"}
