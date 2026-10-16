"""Yourator, career boards and the routing between sources, with the network faked."""
import json

import pytest

from tw_jobs_mcp import boards, http, render, service, workday, yourator

GH_JOBS = {"jobs": [
    {"id": 1, "title": "SRE", "company_name": "Appier", "location": {"name": "Taipei, Taiwan"},
     "absolute_url": "https://g/1", "updated_at": "2026-10-01T00:00:00Z"},
    {"id": 2, "title": "Chef", "company_name": "Appier", "location": {"name": "Tokyo, Japan"},
     "absolute_url": "https://g/2", "updated_at": "2026-10-02T00:00:00Z"},
]}
LEVER_JOBS = [
    {"id": "a", "text": "Backend", "hostedUrl": "https://l/a", "createdAt": 1790000000000,
     "categories": {"location": "Taipei", "allLocations": ["Taipei", "Remote"], "team": "Eng"},
     "workplaceType": "remote"},
    {"id": "b", "text": "Sales", "hostedUrl": "https://l/b", "categories": {"location": "Berlin"}},
]


def _api_row(n, path_slug="co"):
    return {"name": f"job{n}", "path": f"/companies/{path_slug}/jobs/{n}", "company": {"brand": "Co"},
            "salary": "NT$ 50,000 - 80,000 (月薪)", "location": "臺北市", "tags": ["x"],
            "lastActiveAt": "一週內更新"}


@pytest.fixture
def fake(monkeypatch):
    calls = []

    def get_json(url, *, referer=None, params=None):
        calls.append((url, params))
        if "greenhouse" in url:
            return GH_JOBS
        if "lever" in url:
            return LEVER_JOBS
        page = dict(params)["page"]
        rows = [_api_row(n) for n in range((page - 1) * 20, page * 20)]
        return {"payload": {"jobs": rows, "hasMore": page < 4}}

    monkeypatch.setattr(http, "get_json", get_json)
    monkeypatch.setenv("TW_JOBS_BOARDS", "-g:ubiquiti,-g:canonical,-g:stripe,-g:mongodb,-g:appier,-l:pinkoi,"
                                          "-l:binance,-l:crypto,g:appier,l:x")
    return calls


def test_boards_env_adds_and_removes(monkeypatch):
    monkeypatch.setenv("TW_JOBS_BOARDS", "g:gitlab, -g:stripe")
    got = boards.configured()
    assert "g:gitlab" in got and "g:stripe" not in got and "g:appier" in got


def test_boards_keep_only_taiwan_and_dedupe_locations(fake):
    page, notes = boards.search(keyword="", areas=[], remote=False, page=1, per_page=20)
    assert not notes
    assert sorted(r["title"] for r in page["jobs"]) == ["Backend", "SRE"]
    lever = next(r for r in page["jobs"] if r["title"] == "Backend")
    assert lever["location"] == "Taipei" and lever["remote"] == "完全遠端"


def test_boards_filters_and_failure_note(fake, monkeypatch):
    page, _ = boards.search(keyword="sre", areas=[], remote=False, page=1, per_page=20)
    assert [r["title"] for r in page["jobs"]] == ["SRE"]
    page, _ = boards.search(keyword="", areas=[], remote=True, page=1, per_page=20)
    assert [r["title"] for r in page["jobs"]] == ["Backend"]
    monkeypatch.setenv("TW_JOBS_BOARDS", "g:appier,oops")
    _, notes = boards.search(keyword="", areas=[], remote=False, page=1, per_page=20)
    assert len(notes) == 1 and "oops" in notes[0]


def test_yourator_paging_covers_fixed_site_pages(fake):
    out = yourator.search(keyword="x", areas=["台北市"], newest=True, page=2, per_page=30)
    assert [j["title"] for j in out["jobs"]][0] == "job30" and len(out["jobs"]) == 30
    assert out["has_next"]
    fetched = [dict(p)["page"] for _, p in fake]
    assert fetched == [2, 3]
    assert ("area[]", "TPE") in fake[0][1] and ("sort", "recent_updated") in fake[0][1]
    assert yourator.area_codes(["台北市", "新竹縣", "火星"]) == ["TPE", "HSQ"]


def test_yourator_row_ids_and_pay(fake):
    row = yourator.search(keyword="", areas=[], newest=False, page=1, per_page=1)["jobs"][0]
    assert row["id"] == "y:co/0" and row["company_id"] == "y:co"
    assert row["pay"] == {"unit": "月薪", "min": 50000, "max": 80000}


def test_source_validation_and_ignored_filters(fake):
    assert "source" in service.search_jobs(source="mars")["error"]
    out = service.search_jobs(source="yourator", salary_min=1, education="大學", per_page=1)
    assert out["notes"] == ["yourator 未套用：salary_min、education"]
    assert "未套用" in render.search(out)


def test_all_merges_round_robin_and_survives_one_failure(fake, monkeypatch):
    monkeypatch.setattr(service.api, "search", lambda params: (_ for _ in ()).throw(http.SiteError("擋住了")))
    monkeypatch.setattr(service.workday, "search", lambda **kw: (_ for _ in ()).throw(http.SiteError("也擋住")))
    out = service.search_jobs(source="all", per_page=4)
    assert any(n.startswith("104：") for n in out["notes"]) and any(n.startswith("workday：") for n in out["notes"])
    assert {j["id"][:2] for j in out["jobs"]} <= {"y:", "g:", "l:"}
    assert set(out["totals"]) == {"yourator", "boards"}
    assert "yourator" in render.search(out).splitlines()[0]


def test_id_prefix_routes_to_the_right_source(monkeypatch):
    hit = []
    monkeypatch.setattr(yourator, "job", lambda raw: hit.append(("y", raw)) or {})
    monkeypatch.setattr(boards, "job", lambda raw: hit.append(("b", raw)) or {})
    monkeypatch.setattr(workday, "job", lambda raw: hit.append(("w", raw)) or {})
    monkeypatch.setattr(service.api, "job", lambda raw: hit.append(("104", raw)) or {})
    for raw in ("y:co/7", "g:appier/9", "l:pinkoi/z", "w:nvidia/Taiwan-Taipei/X_1", "8qgan"):
        service.get_job(raw)
    assert hit == [("y", "co/7"), ("b", "g:appier/9"), ("b", "l:pinkoi/z"), ("w", "nvidia/Taiwan-Taipei/X_1"),
                   ("104", "8qgan")]


def test_posted_column_keeps_relative_text():
    assert render._posted("2026-10-15") == "10-15"
    assert render._posted("一週內更新") == "一週內更新"


def test_json_format_includes_notes(fake, monkeypatch):
    from tw_jobs_mcp import server
    monkeypatch.setenv("TW_JOBS_FORMAT", "json")
    data = json.loads(server.search_jobs(source="yourator", salary_min=5, per_page=1))
    assert data["notes"]


def test_status_names_unreachable_sources(monkeypatch):
    def fake_get(url, **kw):
        if "yourator" in url:
            raise http.SiteError("403 被擋")
        return {"jobs": [], "payload": {"jobs": [], "hasMore": False}}

    monkeypatch.setattr(http, "get_json", fake_get)
    monkeypatch.setattr(service.api, "search", lambda params: {})
    monkeypatch.setenv("TW_JOBS_BOARDS", "-g:ubiquiti,-g:canonical,-g:stripe,-g:mongodb,-l:pinkoi,-l:binance,-l:crypto")
    text = render.status(service.source_status())
    assert text.startswith("可用：104、g:appier") and "無法連線 yourator：403 被擋" in text


# ---- Workday -------------------------------------------------------------------

FACETS = [{"facetParameter": "locationMainGroup", "values": [
    {"facetParameter": "locations", "values": [
        {"id": "tpe", "descriptor": "Taiwan, Taipei"}, {"id": "hsz", "descriptor": "Taiwan, Hsinchu"},
        {"id": "sg", "descriptor": "Singapore"}]}]}]


def _post(listing):
    def post_json(url, body, *, referer=None):
        if body["limit"] == 1:
            return {"total": 2, "facets": FACETS, "jobPostings": []}
        return listing(body)
    return post_json


def _posting(n):
    return {"title": f"Job {n}", "externalPath": f"/job/Taiwan-Taipei/Job-{n}_R{n}",
            "locationsText": "2 Locations", "postedOn": "Posted 3 Days Ago"}


def test_workday_filters_to_taiwan_and_cities(monkeypatch):
    seen = []

    def listing(body):
        seen.append(body)
        return {"total": 2, "jobPostings": [_posting(1), _posting(2)]}

    monkeypatch.setattr(http, "post_json", _post(listing))
    monkeypatch.setenv("TW_JOBS_WORKDAY", "-" + ",-".join(c for c in workday.DEFAULT_COMPANIES if c != "nvidia"))
    page, notes = workday.search(keyword="gpu", areas=["新竹市"], page=1, per_page=5)
    assert seen[0]["appliedFacets"] == {"locations": ["hsz"]} and seen[0]["searchText"] == "gpu"
    assert page["total"] == 2 and not notes
    row = page["jobs"][0]
    assert row["id"] == "w:nvidia/Taiwan-Taipei/Job-1_R1" and row["location"] == "Taiwan Taipei"
    assert row["posted"] == "3天前" and row["company"] == "NVIDIA"
    nobody, _ = workday.search(keyword="", areas=["高雄市"], page=1, per_page=5)
    assert nobody["jobs"] == []  # no Kaohsiung location, so nothing is asked for


def test_workday_env_adds_and_rejects(monkeypatch):
    monkeypatch.setenv("TW_JOBS_WORKDAY", "acme.wd1/External,-micron")
    table = workday.companies()
    assert table["acme"] == ("wd1", "External", "Acme") and "micron" not in table
    monkeypatch.setenv("TW_JOBS_WORKDAY", "nonsense")
    with pytest.raises(http.SiteError):
        workday.companies()


def test_workday_detail_and_labels(monkeypatch):
    monkeypatch.setattr(http, "get_json", lambda url, **kw: {"jobPostingInfo": {
        "title": "SWE", "location": "Taiwan, Taipei", "additionalLocations": ["Taiwan, Hsinchu"],
        "jobDescription": "<p>Hi &amp; bye</p>", "postedOn": "超過 30 天前刊登", "timeType": "Full time",
        "jobReqId": "R1", "externalUrl": "https://x/y"}})
    d = workday.job("nvidia/Taiwan-Taipei/SWE_R1")
    assert d["id"] == "w:nvidia/Taiwan-Taipei/SWE_R1" and d["location"] == "Taiwan, Taipei；Taiwan, Hsinchu"
    assert d["posted"] == "30+天前" and "Hi & bye" in d["description"]
    assert [workday._ago(x) for x in ("Posted Today", "昨天", "5 天前刊登")] == ["今天", "昨天", "5天前"]
