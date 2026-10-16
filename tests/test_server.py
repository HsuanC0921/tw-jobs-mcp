import pytest

from tw_jobs_mcp import service
from tw_jobs_mcp.j104 import api
from tw_jobs_mcp.http import SiteError


@pytest.fixture
def seen(monkeypatch):
    """Capture search params; the fake 104 answers with one ad and one real job."""
    box = {}

    def fake_search(params):
        box["params"] = params
        rows = [("ad", "1"), ("real", "0")]
        paging = dict(total=1, currentPage=1, lastPage=1)
        return {
            "data": [{"jobName": n, "jobType": t, "link": {"job": f"https://x/job/{n}"}} for n, t in rows],
            "metadata": {"pagination": paging},
        }

    monkeypatch.setattr(api, "search", fake_search)
    return box


def test_search_filters_ads_and_passes_params(seen):
    out = service.search_jobs(keyword="python", salary_min=60000)
    assert [j["id"] for j in out["jobs"]] == ["real"]
    assert seen["params"]["sctp"] == "M"


def test_bad_argument_never_reaches_104(seen):
    assert "sort" in service.search_jobs(sort="亂寫")["error"]
    assert "params" not in seen


def test_ambiguous_area_is_widened_with_a_note(seen):
    out = service.search_jobs(area=["中山區"])
    assert any("已全部納入" in n for n in out["notes"]) and "," in seen["params"]["area"]


def test_site_error_becomes_error_dict(monkeypatch):
    def boom(_):
        raise SiteError("壞掉了")

    monkeypatch.setattr(api, "search", boom)
    assert service.search_jobs() == {"error": "壞掉了"}


def test_empty_ids_rejected():
    assert "error" in service.get_job("  ")
    assert "error" in service.get_company("")


def test_company_not_found(monkeypatch):
    monkeypatch.setattr(api, "company", lambda _: {"data": {"custName": None}})
    assert "找不到公司" in service.get_company("zzz")["error"]


def test_company_with_openings(monkeypatch):
    monkeypatch.setattr(api, "company", lambda _: {"data": {"custName": "ACME", "custNo": "abc"}})
    monkeypatch.setattr(api, "company_jobs", lambda _: {"data": {"list": {"normalJobs": [{"jobNo": "j1"}]}}})
    out = service.get_company("abc", with_openings=True)
    assert out["name"] == "ACME" and out["openings"][0]["id"] == "j1"


def test_lookup_code():
    assert any("大安" in m["name"] for m in service.lookup_code("area", "台北市大安")["matches"])
    assert "error" in service.lookup_code("foo", "台北")
