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


def company_jobs(company_id: str, page: int = 1, size: int = 10, keyword: str = "") -> dict:
    """keyword is the company page's own search box; it also matches the job description."""
    params = {"page": str(page), "pageSize": str(size)} | ({"keyword": keyword} if keyword else {})
    return http.get_json(
        f"{_ROOT}/api/companies/{company_id}/jobs", params=params, referer=f"{_ROOT}/company/{company_id}"
    )


def similar_jobs(job_id: str) -> dict:
    return http.get_json(f"{_ROOT}/job/ajax/similarJobs/{job_id}", params={"page": "1"},
                         referer=f"{_ROOT}/job/{job_id}")


def applicants(job_id: str) -> dict:
    """Who applied in the last two weeks, as shares. The endpoint wants the decimal job number,
    which is the base-36 id read as a number."""
    number = str(int(job_id, 36))
    return http.get_json(f"{_ROOT}/jb/104i/applyAnalysisToJob/all", params={"job_no": number},
                         referer=f"{_ROOT}/jobs/apply/analysis/{job_id}")
