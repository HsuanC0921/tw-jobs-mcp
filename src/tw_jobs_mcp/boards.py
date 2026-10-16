"""Foreign companies' own career boards, filtered to their Taiwan openings.

Greenhouse and Lever publish job-board APIs meant to be read by anyone, which makes them
a clean way to reach the foreign-company and rare roles 104 under-represents. The boards
below were checked to list Taiwan roles. Extend or trim them with TW_JOBS_BOARDS, e.g.
TW_JOBS_BOARDS="g:gitlab,l:kraken,-g:stripe" (g: Greenhouse, l: Lever, leading - removes).
"""
import os
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from . import http, text
from .j104.shape import blank_detail, blank_page, blank_row

DEFAULT_BOARDS = ("g:appier", "g:ubiquiti", "g:canonical", "g:stripe", "g:mongodb",
                  "l:pinkoi", "l:binance", "l:crypto")
_GH = "https://boards-api.greenhouse.io/v1/boards"
_LEVER = "https://api.lever.co/v0/postings"
_TAIWAN = re.compile(r"taiwan|taipei|hsinchu|taichung|kaohsiung|tainan|台灣|台北", re.I)
_CITIES = {"臺北": "taipei", "新北": "new taipei", "桃園": "taoyuan", "新竹": "hsinchu",
           "臺中": "taichung", "臺南": "tainan", "高雄": "kaohsiung"}
_PER = {"per-year-salary": "年薪", "per-month-salary": "月薪", "per-hour-wage": "時薪", "per-day-wage": "日薪"}


def configured() -> list[str]:
    boards = list(DEFAULT_BOARDS)
    for item in filter(None, (x.strip() for x in os.environ.get("TW_JOBS_BOARDS", "").split(","))):
        if item.startswith("-"):
            boards = [b for b in boards if b != item[1:]]
        elif item not in boards:
            boards.append(item)
    return boards


def _split(board: str) -> tuple[str, str]:
    kind, _, name = board.partition(":")
    if kind not in ("g", "l") or not name:
        raise http.SiteError(f"看不懂的職缺板 '{board}'，格式為 g:名稱（Greenhouse）或 l:名稱（Lever）")
    return kind, name


def _day(millis) -> str:
    if not millis:
        return ""
    return datetime.fromtimestamp(int(millis) / 1000, timezone.utc).strftime("%Y-%m-%d")


def _row(kind: str, name: str, raw: dict) -> dict:
    if kind == "g":
        where = raw["location"]["name"]
        return blank_row(
            id=f"g:{name}/{raw['id']}", title=raw["title"], company=raw.get("company_name", name),
            company_id=f"g:{name}", location=where, url=raw["absolute_url"],
            remote="完全遠端" if "remote" in where.lower() else "",
            posted=(raw.get("updated_at") or raw.get("first_published") or "")[:10])
    cats, pay = raw.get("categories") or {}, raw.get("salaryRange") or {}
    places = dict.fromkeys(x for x in (cats.get("location"), *(cats.get("allLocations") or [])) if x)
    where = ", ".join(p for p in places if _TAIWAN.search(p)) or ", ".join(places)
    unit = _PER.get(pay.get("interval", ""))
    twd = pay.get("currency") in ("TWD", "NTD")
    return blank_row(
        id=f"l:{name}/{raw['id']}", title=raw["text"], company=name.title(), company_id=f"l:{name}",
        location=where, url=raw["hostedUrl"], skills=[cats["team"]] if cats.get("team") else [],
        remote="完全遠端" if raw.get("workplaceType") == "remote" else "",
        pay={"unit": unit, "min": pay.get("min"), "max": pay.get("max")} if unit and twd else None,
        posted=_day(raw.get("createdAt")))


def _board_rows(board: str) -> list[dict]:
    kind, name = _split(board)
    if kind == "g":
        raw = http.get_json(f"{_GH}/{name}/jobs")["jobs"]
        taiwan = [j for j in raw if _TAIWAN.search(j["location"]["name"])]
    else:
        raw = http.get_json(f"{_LEVER}/{name}", params={"mode": "json"})
        taiwan = [j for j in raw if _TAIWAN.search(" ".join(
            [str((j.get("categories") or {}).get("location", "")),
             *((j.get("categories") or {}).get("allLocations") or [])]))]
    return [_row(kind, name, j) for j in taiwan]


def _wanted(row: dict, words: list[str], cities: list[str]) -> bool:
    haystack = f"{row['title']} {row['company']} {' '.join(row['skills'])}".lower()
    if not all(w in haystack for w in words):
        return False
    where = row["location"].lower()
    # a posting that only says "Taiwan" could be anywhere on the island, so it stays
    return not cities or any(c in where for c in cities) or not any(c in where for c in _CITIES.values())


def search(*, keyword: str, areas: list[str], remote: bool, page: int, per_page: int,
           only: str | None = None) -> tuple[dict, list[str]]:
    """(page, notes). A board that fails is skipped and named in the notes."""
    boards = [only] if only else configured()

    def load(board):
        try:
            return _board_rows(board), None
        except (http.SiteError, KeyError, TypeError) as exc:
            return [], f"{board}：{exc}"

    with ThreadPoolExecutor(max_workers=min(8, len(boards) or 1)) as pool:
        loaded = list(pool.map(load, boards))
    notes = [n for _, n in loaded if n]
    words = keyword.lower().split()
    cities = [_CITIES[c] for c in (a.replace("台", "臺")[:2] for a in areas) if c in _CITIES]
    rows = [r for rows, _ in loaded for r in rows if _wanted(r, words, cities) and (r["remote"] or not remote)]
    rows.sort(key=lambda r: r["posted"], reverse=True)  # boards have no relevance score
    start = (page - 1) * per_page
    return blank_page(rows[start:start + per_page], len(rows), page, start + per_page < len(rows)), notes


def job(raw_id: str) -> dict:
    board, _, number = raw_id.partition("/")
    kind, name = _split(board)
    if kind == "g":
        d = http.get_json(f"{_GH}/{name}/jobs/{number}", params={"pay_transparency": "true"})
        pay = d.get("pay_input_ranges") or []
        return blank_detail(
            id=raw_id, url=d["absolute_url"], title=d["title"], company=d.get("company_name", name),
            company_id=f"g:{name}", posted=(d.get("first_published") or "")[:10],
            categories=[x["name"] for x in d.get("departments") or []], location=d["location"]["name"],
            salary="；".join(
                f"{p['title']} {p['min_cents'] // 100:,}~{p['max_cents'] // 100:,} {p['currency_type']}"
                for p in pay),
            description=text.strip_html(d.get("content", "")))
    d = http.get_json(f"{_LEVER}/{name}/{number}")
    cats, pay = d.get("categories") or {}, d.get("salaryRange") or {}
    sections = "\n".join(f"{s['text']}\n{text.strip_html(s['content'])}" for s in d.get("lists") or [])
    return blank_detail(
        id=raw_id, url=d["hostedUrl"], title=d["text"], company=name.title(), company_id=f"l:{name}",
        categories=[x for x in (cats.get("department"), cats.get("team")) if x],
        posted=_day(d.get("createdAt")), location=cats.get("location", ""),
        remote="完全遠端" if d.get("workplaceType") == "remote" else "",
        salary=f"{pay.get('min', '')}~{pay.get('max', '')} {pay.get('currency', '')}" if pay else "",
        description="\n".join(x for x in (d.get("descriptionPlain", ""), sections, d.get("additionalPlain", "")) if x))


def company(raw_id: str, with_openings: bool) -> dict:
    kind, name = _split(raw_id)
    title = name.title()
    if kind == "g":
        title = http.get_json(f"{_GH}/{name}").get("name", title)
    info = {"id": raw_id, "name": title, "industry": "", "employees": "", "capital": "", "address": "",
            "website": "", "profile": "", "products": "", "welfare": "", "followers": 0,
            "url": f"https://job-boards.greenhouse.io/{name}" if kind == "g" else f"https://jobs.lever.co/{name}"}
    if with_openings:
        info["openings"] = [
            {"id": r["id"], "title": r["title"], "salary": "待遇面議", "location": r["location"], "experience": ""}
            for r in _board_rows(raw_id)]
    return info
