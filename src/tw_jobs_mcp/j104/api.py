"""The 104 endpoints, one function each."""
from .. import http

_ROOT = "https://www.104.com.tw"


def search(params: dict) -> dict:
    return http.get_json(
        f"{_ROOT}/jobs/search/api/jobs",
        params={"jobsource": "joblist_search", "mode": "s", **params},
        referer=f"{_ROOT}/jobs/search/",
    )


def job(job_id: str) -> dict:
    return http.get_json(f"{_ROOT}/job/ajax/content/{job_id}", referer=f"{_ROOT}/job/{job_id}")


def company(company_id: str) -> dict:
    return http.get_json(
        f"{_ROOT}/api/companies/{company_id}/content", referer=f"{_ROOT}/company/{company_id}"
    )


def company_jobs(company_id: str, page: int = 1, size: int = 10) -> dict:
    return http.get_json(
        f"{_ROOT}/api/companies/{company_id}/jobs",
        params={"page": str(page), "pageSize": str(size)},
        referer=f"{_ROOT}/company/{company_id}",
    )
