"""Hits the real 104 site. Run with: uv run pytest -m live"""
import pytest

from tw_jobs_mcp import service

pytestmark = pytest.mark.live


def test_filters_really_apply():
    base = service.search_jobs(keyword="工程師", per_page=10)
    assert len(base["jobs"]) == 10 and not any(j["sponsored"] for j in base["jobs"])

    paid = service.search_jobs(keyword="工程師", salary_min=70000, per_page=10)
    assert 0 < paid["total"] < base["total"] / 5
    assert all(j["salary"] != "待遇面議" for j in paid["jobs"])

    taipei = service.search_jobs(keyword="工程師", area=["台北市"], per_page=10)
    assert all(j["location"].startswith("台北市") for j in taipei["jobs"])

    remote = service.search_jobs(keyword="工程師", remote=True, per_page=10)
    assert all(j["remote"] for j in remote["jobs"])

    assert service.search_jobs(keyword="工程師", job_type="兼職", per_page=1)["total"] < base["total"] / 10
    assert service.search_jobs(keyword="工程師", my_years=2, per_page=1)["total"] < base["total"]


def test_job_and_company_round_trip():
    job_id = service.search_jobs(keyword=".NET", per_page=3)["jobs"][0]["id"]
    job = service.get_job(job_id)
    assert job["title"] and job["company_id"]
    company = service.get_company(job["company_id"], with_openings=True)
    assert company["name"] and isinstance(company["openings"], list)


def test_bad_ids_report_cleanly():
    assert "404" in service.get_job("zzzzz")["error"]
    assert "找不到公司" in service.get_company("zzzzzz")["error"]
