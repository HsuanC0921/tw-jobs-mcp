"""Reshape 104's raw JSON into small, readable dicts. Pure functions, no I/O."""

_UNIT = {30: "時薪", 40: "日薪", 50: "月薪", 60: "年薪"}
_NO_CEILING = 9_999_999  # 104's "no upper limit" marker
_EDUCATION = {2: "高中職", 3: "專科", 4: "大學", 5: "碩士", 6: "博士"}
_REMOTE = {1: "完全遠端", 2: "部分遠端"}


def salary_parts(low: int, high: int, kind: int) -> tuple[str, int | None, int | None] | None:
    """(unit, floor, cap), either bound may be missing; None when negotiable.

    kind is 104's s10: 10 negotiable, 30 hourly, 40 daily, 50 monthly, 60 yearly.
    """
    floor = low or None
    cap = high if 0 < high < _NO_CEILING else None
    if kind == 10 or (floor is None and cap is None):
        return None
    return _UNIT.get(kind, "月薪"), floor, cap


def salary_text(low: int, high: int, kind: int) -> str:
    parts = salary_parts(low, high, kind)
    if parts is None:
        return "待遇面議"
    unit, floor, cap = parts
    if cap is None:
        return f"{unit} {floor:,} 元以上"
    if floor is None:
        return f"{unit} {cap:,} 元以下"
    span = f"{floor:,}" if floor == cap else f"{floor:,}~{cap:,}"
    return f"{unit} {span} 元"


def last_segment(link: str) -> str:
    return link.rstrip("/").rsplit("/", 1)[-1] if link else ""


def _absolute(url: str) -> str:
    return "https:" + url if url.startswith("//") else url


def _day(stamp: str) -> str:
    if len(stamp) == 8 and stamp.isdigit():
        return f"{stamp[:4]}-{stamp[4:6]}-{stamp[6:]}"
    return stamp


def _names(items) -> list[str]:
    return [i["description"] for i in items or [] if isinstance(i, dict) and i.get("description")]


def _years(code) -> str:
    """The list's `period`: 0 is 不拘, n >= 2 is (n - 1) years or more (checked against the postings; 1 never seen)."""
    return "不拘" if code == 0 else f"{code - 1}年+" if isinstance(code, int) and code >= 2 else ""


def search_row(row: dict) -> dict:
    links = row.get("link") or {}
    url = _absolute(links.get("job", ""))
    low, high, kind = row.get("salaryLow", 0), row.get("salaryHigh", 0), row.get("s10", 0)
    parts = salary_parts(low, high, kind)
    return {
        "id": last_segment(url),
        "title": row.get("jobName", ""),
        "company": row.get("custName", ""),
        "company_id": last_segment(links.get("cust", "")),
        "industry": row.get("coIndustryDesc", ""),
        "company_size": row.get("employeeCount") or 0,
        "salary": salary_text(low, high, kind),
        "pay": None if parts is None else {"unit": parts[0], "min": parts[1], "max": parts[2]},
        "location": row.get("jobAddrNoDesc", ""),
        "nearby_mrt": row.get("mrtDesc", ""),
        "hours": row.get("d3", ""),
        "remote": _REMOTE.get(row.get("remoteWorkType"), ""),
        "experience": _years(row.get("period")),
        "education": [_EDUCATION[c] for c in row.get("optionEdu") or [] if c in _EDUCATION],
        "major": row.get("major") or [],
        "skills": _names(row.get("pcSkills")),
        "posted": _day(row.get("appearDate", "")),
        "applicants": row.get("applyCnt", 0),
        "summary": row.get("descSnippet") or row.get("description") or "",
        "url": url,
        # 104 puts two paid listings (jobType 1) at the top of every page.
        "sponsored": str(row.get("jobType")) == "1",
    }


def search_page(payload: dict) -> dict:
    paging = (payload.get("metadata") or {}).get("pagination") or {}
    jobs = [j for j in map(search_row, payload.get("data") or []) if not j["sponsored"]]
    page = paging.get("currentPage", 1)
    pages = paging.get("lastPage", 1)
    return {
        "total": paging.get("total", 0),
        "page": page,
        "pages": pages,
        "has_next": page < pages,
        "jobs": jobs,
    }


def job_detail(payload: dict) -> dict:
    data = payload.get("data") or {}
    head, body, cond = (data.get(k) or {} for k in ("header", "jobDetail", "condition"))
    other = cond.get("other")
    schedule = body.get("workPeriod") or {}
    return {
        "title": head.get("jobName", ""),
        "company": head.get("custName", ""),
        "company_id": last_segment(head.get("custUrl", "")),
        "industry": data.get("industry", ""),
        "company_size": data.get("employees", ""),
        "posted": head.get("appearDate", ""),
        "closes": data.get("closeDate", ""),
        "categories": _names(body.get("jobCategory")),
        "salary": body.get("salary", ""),
        "location": (body.get("addressRegion") or "") + (body.get("addressDetail") or ""),
        "remote": (body.get("remoteWork") or {}).get("description", ""),
        "description": body.get("jobDescription", ""),
        "requirements": {
            "experience": cond.get("workExp", ""),
            "education": cond.get("edu", ""),
            "major": cond.get("major") or [],
            "skills": _names(cond.get("specialty")) + _names(cond.get("skill")),
            "languages": cond.get("language") or [],
            "certificates": _names(cond.get("certificate")),
            "driver_license": _names(cond.get("driverLicense")),
            "other": "；".join(map(str, other)) if isinstance(other, list) else other or "",
        },
        "conditions": {
            "headcount": body.get("needEmp", ""),
            "management": body.get("manageResp", ""),
            "business_trip": body.get("businessTrip", ""),
            "start": body.get("startWorkingDay", ""),
            "shifts": list((schedule.get("shifts") or {}).keys()),
            "hours": schedule.get("note", ""),
            "vacation": body.get("vacationPolicy", ""),
        },
        "welfare": (data.get("welfare") or {}).get("welfare", ""),
        "hr_activity": _hr(data.get("interactionRecord")),
    }


def _hr(record) -> str:
    """104's own wording of how recently the employer handled résumés or replied."""
    record = record or {}
    return "、".join(x for x in (record.get("lastProcessedResumeDesc"), record.get("lastCustReplyDesc")) if x)


def similar_jobs(payload: dict) -> list[dict]:
    rows = (payload.get("data") or {}).get("list") or []
    return [
        {
            "id": last_segment((r.get("link") or {}).get("job", "")),
            "company_id": last_segment((r.get("link") or {}).get("cust", "")),
            "title": r.get("name", ""),
            "company": r.get("custName", ""),
            "salary": r.get("salaryDesc", ""),
            "location": r.get("area", ""),
            "experience": r.get("periodDesc", ""),
            "hr_activity": _hr(r.get("interactionRecord")),
        }
        for r in rows
    ]


# 104's applicant breakdown: (key, label); the first three are one answer per applicant
_GROUPS = (("edu", "學歷"), ("exp", "年資"), ("yearRange", "年齡"),
           ("major", "科系"), ("language", "語言"), ("skill", "技能"), ("cert", "證照"))


def _headcount(shares: list[float]) -> int | None:
    """The smallest number of applicants whose whole-person splits round to every share.

    104 hides the count but publishes two-decimal percentages; 28.57/71.43 can only be 2 of 7
    (or 4 of 14, which is why this is a floor and not a certainty).
    """
    if not shares:
        return 0
    for n in range(1, 1000):
        if all(abs(round(p * n / 100) * 100 / n - p) < 0.006 for p in shares):
            return n
    return None


def applicants(payload: dict) -> dict:
    groups = {}
    for key, label in _GROUPS:
        found = []
        for item in (payload.get(key) or {}).values():
            if isinstance(item, dict) and float(item.get("percent") or 0) > 0:
                name = next((str(v).strip() for k, v in item.items() if k.endswith("Name")), "")
                found.append((name, round(float(item["percent"]), 1)))
        groups[label] = sorted(found, key=lambda x: -x[1])
    single = [float(i["percent"]) for key, _ in _GROUPS[:3] for i in (payload.get(key) or {}).values()
              if isinstance(i, dict) and float(i.get("percent") or 0) > 0]
    return {"at_least": _headcount(single), "groups": groups}


def company(payload: dict) -> dict | None:
    """None when 104 answers 200 with an empty shell (unknown company id)."""
    data = payload.get("data") or {}
    if not data.get("custName"):
        return None
    return {
        "id": data.get("custNo", ""),
        "name": data["custName"],
        "industry": data.get("industryDesc", ""),
        "employees": data.get("empNo", ""),
        "capital": data.get("capital", ""),
        "address": data.get("address", ""),
        "website": (data.get("custLink") or "").strip(),
        "profile": data.get("profile", ""),
        "products": data.get("product", ""),
        "welfare": data.get("welfare", ""),
        "followers": int(data.get("followerCount") or 0),
        "url": f"https://www.104.com.tw/company/{data.get('custNo', '')}",
    }


def company_openings(payload: dict) -> list[dict]:
    listing = ((payload.get("data") or {}).get("list")) or {}
    rows = (listing.get("topJobs") or []) + (listing.get("normalJobs") or [])
    return [
        {
            "id": r.get("jobNo", ""),
            "title": r.get("jobName", ""),
            "salary": r.get("jobSalaryDesc") or "待遇面議",
            "location": r.get("jobAddrNoDesc", ""),
            "experience": r.get("periodDesc", ""),
            "url": r.get("jobUrl", ""),
        }
        for r in rows
    ]


def blank_row(**fields) -> dict:
    """A search row with every key the renderer reads; other sources fill what they have."""
    row = {"id": "", "title": "", "company": "", "company_id": "", "industry": "", "company_size": 0,
           "salary": "", "pay": None, "location": "", "nearby_mrt": "", "hours": "", "remote": "",
           "education": [], "major": [], "skills": [], "posted": "", "applicants": 0, "summary": "",
           "url": "", "sponsored": False}
    return {**row, **fields}


def blank_detail(**fields) -> dict:
    """A job detail with every key the renderer reads."""
    detail = {
        "id": "", "url": "", "title": "", "company": "", "company_id": "", "industry": "",
        "company_size": "", "posted": "", "closes": "", "categories": [], "salary": "",
        "location": "", "remote": "", "description": "", "welfare": "", "hr_activity": "",
        "requirements": {"experience": "", "education": "", "major": [], "skills": [],
                         "languages": [], "certificates": [], "driver_license": [], "other": ""},
        "conditions": {"headcount": "", "management": "", "business_trip": "", "start": "",
                       "shifts": [], "hours": "", "vacation": ""},
    }
    return {**detail, **fields}


def blank_page(jobs: list[dict], total: int, page: int = 1, has_next: bool = False) -> dict:
    return {"total": total, "page": page, "pages": page + has_next, "has_next": has_next, "jobs": jobs}
