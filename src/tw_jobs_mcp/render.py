"""Turn result dicts into compact text. A table row costs far fewer tokens than the
same job as JSON, where every row repeats every key."""

_UNIT = {"月薪": "月", "年薪": "年", "日薪": "日", "時薪": "時"}
DESC_LIMIT = 1500
BLURB_LIMIT = 400


def _t(value) -> str:
    return str(value).replace("|", "/").replace("\n", " ").strip()


def _clip(text: str, limit: int, hint: str = "") -> str:
    text = text.strip()
    return text if len(text) <= limit else f"{text[:limit]}…（共 {len(text)} 字{hint}）"


def pay(p: dict | None) -> str:
    if not p:
        return "面議"
    low, high, unit = p["min"], p["max"], _UNIT.get(p["unit"], p["unit"])
    if low is not None and high is not None:
        span = f"{low}" if low == high else f"{low}~{high}"
    else:
        span = f"{low}+" if low is not None else f"~{high}"
    return unit + span


def _education(names: list[str]) -> str:
    return names[0] if len(names) == 1 else f"{names[0]}~{names[-1]}" if names else ""


def _posted(stamp: str) -> str:
    """MM-DD for a full date; other text, such as Yourator's relative wording, stays as it is."""
    return stamp[5:] if len(stamp) == 10 and stamp[4] == "-" else stamp


def _job_row(j: dict) -> str:
    where = j["location"] + ("（遠端）" if j["remote"] == "完全遠端" else "（部分遠端）" if j["remote"] else "")
    cols = [j["id"], j["company_id"], j["title"], j["company"], pay(j["pay"]), where,
            _education(j["education"]), "/".join(j["skills"][:5]), _posted(j["posted"])]
    return "|".join(_t(c) for c in cols)


def search(page: dict) -> str:
    notes = [f"註：{n}" for n in page.get("notes", ())]
    if not page["jobs"]:
        return "\n".join([f"無結果（共 {page['total']} 筆）。試著拿掉薪資、學歷等條件，或改 source=all", *notes])
    split = "（" + "、".join(f"{k} {v}" for k, v in page["totals"].items()) + "）" if "totals" in page else ""
    more = "+" if page.get("at_least") else ""  # Yourator reports no total, only that more exist
    head = (f"共 {page['total']}{more} 筆{split}，第 {page['page']}/{page['pages']}{more} 頁\n"
            "id|company_id|職稱|公司|薪資|地點|學歷|技能|刊登")
    return "\n".join([head, *map(_job_row, page["jobs"]), *notes])


def _line(*pairs: tuple[str, object]) -> str:
    return " ".join(f"{k}:{_t(v)}" for k, v in pairs if v)


def job(d: dict, full: bool = False) -> str:
    r, c = d["requirements"], d["conditions"]
    skills = "/".join(r["skills"])
    lines = [
        f"{d['title']}｜{d['company']}｜{_t(d['industry'])} {_t(d['company_size'])}".strip(),
        _line(("id", d["id"]), ("company_id", d["company_id"]), ("url", d["url"])),
        _line(("薪資", d["salary"]), ("地點", d["location"]), ("遠端", d["remote"]),
              ("刊登", d["posted"]), ("截止", d["closes"])),
        _line(("職類", "/".join(d["categories"]))),
        _line(("經驗", r["experience"]), ("學歷", r["education"]), ("科系", "/".join(r["major"])),
              ("技能", skills), ("證照", "/".join(r["certificates"])),
              ("駕照", "/".join(r["driver_license"])), ("其他", r["other"])),
        _line(("工時", " ".join(c["shifts"]) + " " + c["hours"]), ("假別", c["vacation"]),
              ("出差", c["business_trip"]), ("到職", c["start"]), ("名額", c["headcount"]),
              ("管理", c["management"])),
        _line(("福利", d["welfare"] if full else _clip(d["welfare"], BLURB_LIMIT))),
        "說明：" + (d["description"].strip() if full else _clip(d["description"], DESC_LIMIT, "，full=True 看全文")),
    ]
    return "\n".join(x for x in lines if x.strip())


def company(d: dict, full: bool = False) -> str:
    clip = (lambda s: s.strip()) if full else (lambda s: _clip(s, BLURB_LIMIT, "，full=True 看全文"))
    lines = [
        f"{d['name']}｜{_t(d['industry'])}｜員工 {_t(d['employees'])}｜資本額 {_t(d['capital'])}",
        _line(("id", d["id"]), ("地址", d["address"]), ("網站", d["website"]),
              ("追蹤", d["followers"]), ("url", d["url"])),
        _line(("簡介", clip(d["profile"])), ("產品", clip(d["products"])), ("福利", clip(d["welfare"]))),
    ]
    if d.get("note"):
        lines.append(d["note"])
    if d.get("openings") is not None:
        lines.append("目前職缺 id|職稱|薪資|地點|年資" if d["openings"] else "目前無職缺")
        lines += ["|".join(_t(o[k]) for k in ("id", "title", "salary", "location", "experience"))
                  for o in d["openings"]]
    return "\n".join(x for x in lines if x.strip())


def overview(d: dict) -> str:
    head = f"符合 {d['matching_jobs']} 筆，取樣 {d['sampled']} 筆，未公開薪資 {d['undisclosed_share']:.0%}"
    rows = []
    for unit, s in d["by_unit"].items():
        quart = f" p25 {s['p25']} p75 {s['p75']}" if "p25" in s else ""
        rows.append(f"{unit} n={s['count']} 最低 {s['min']} 中位 {s['median']} 最高 {s['max']}{quart}")
    if not rows:
        head += "（沒有可統計的薪資）"
    return "\n".join([head, *rows, *[f"註：{n}" for n in d.get("notes", ())]])


def codes(found: list[dict]) -> str:
    return "\n".join(f"{m['code']} {m['name']}" for m in found) or "無符合項目"


def status(d: dict) -> str:
    bad = [s for s in d["sources"] if s["error"]]
    good = [s["name"] for s in d["sources"] if not s["error"]]
    # career sites come by the dozen; name only the main sources and count the rest
    boards = sum(n[:2] in ("g:", "l:") for n in good)
    workday = sum(n.startswith("w:") for n in good)
    shown = [n for n in good if ":" not in n] + [f"職缺板 {boards} 家"] * bool(boards) + [f"Workday {workday} 家"] * bool(workday)
    lines = ["可用：" + "、".join(shown) if good else "沒有可用的來源"]
    lines += [f"無法連線 {s['name']}：{_t(s['error'])[:120]}" for s in bad]
    return "\n".join(lines)


def failure(d: dict) -> str:
    return f"錯誤：{d['error']}"
