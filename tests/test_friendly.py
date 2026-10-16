"""Loose arguments are repaired, widened or relaxed instead of rejected."""
from tw_jobs_mcp import friendly, service
from tw_jobs_mcp.j104 import api


def _page(total):
    return {"data": [{"jobName": "j", "jobType": "0", "link": {"job": "https://x/job/abc"}}] * bool(total),
            "metadata": {"pagination": {"total": total, "currentPage": 1, "lastPage": 1}}}


def test_places_and_categories_degrade_gracefully():
    f, notes = friendly.normalize({"area": ["台北", "新北", "Mars"], "jobcat": ["後端", "工程師"], "keyword": "ai"})
    assert len(f["area"]) == 2 and any("Mars" in n and "不限地區" in n for n in notes)
    assert f["keyword"] == "ai 工程師" and len(f["jobcat"]) == 1  # 後端 resolved, 工程師 became a keyword


def test_paging_is_clamped_not_rejected():
    f, notes = friendly.normalize({"per_page": 999, "page": 0, "my_years": -3})
    assert (f["per_page"], f["page"], f["my_years"]) == (30, 1, 0) and notes


def test_relaxations_drop_one_more_filter_each_time():
    steps = list(friendly.relaxations({"salary_min": 9, "education": "大學", "remote": True, "keyword": "x"}))
    assert [d for _, d in steps] == [["remote"], ["remote", "education"], ["remote", "education", "salary_min"]]
    assert steps[-1][0]["salary_min"] is None and steps[-1][0]["keyword"] == "x"


def test_empty_search_is_relaxed_then_reported(monkeypatch):
    sent = []

    def fake(params):
        sent.append(params)
        return _page(0 if "scmin" in params else 5)

    monkeypatch.setattr(api, "search", fake)
    out = service.search_jobs(keyword="x", salary_min=900000)
    assert out["total"] == 3 and any("已放寬：不限salary_min" in n for n in out["notes"])


def test_nothing_on_104_falls_back_to_other_sources(monkeypatch):
    monkeypatch.setattr(api, "search", lambda params: _page(0))
    seen = []

    def fake_run(names, f):
        seen.append(names)
        return {"total": 3 if names != ("104",) else 0, "page": 1, "pages": 1, "has_next": False,
                "jobs": [], "notes": []}

    monkeypatch.setattr(service, "_run", fake_run)
    out = service.search_jobs(keyword="x")
    assert out["total"] == 3 and seen == [("104",), service.SOURCES[1:]]
    assert any("改查其他來源" in n for n in out["notes"])


