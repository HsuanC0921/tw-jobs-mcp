import pytest

from tw_jobs_mcp import http
from tw_jobs_mcp.j104 import shape


@pytest.mark.parametrize("args,text", [
    ((32000, 38000, 50), "月薪 32,000~38,000 元"),
    ((0, 9_999_999, 10), "待遇面議"),
    ((0, 0, 50), "待遇面議"),
    ((50000, 9_999_999, 50), "月薪 50,000 元以上"),
    ((0, 80000, 50), "月薪 80,000 元以下"),
    ((45000, 45000, 50), "月薪 45,000 元"),
    ((1_200_000, 2_000_000, 60), "年薪 1,200,000~2,000,000 元"),
    ((300, 400, 30), "時薪 300~400 元"),
])
def test_salary_text(args, text):
    assert shape.salary_text(*args) == text


def _row(no, kind, **extra):
    return {"jobName": no, "jobType": kind, "link": {"job": f"//www.104.com.tw/job/{no}"}, **extra}


def test_list_experience_codes():
    assert [shape._years(c) for c in (0, 2, 3, 11, 1, None)] == ["不拘", "1年+", "2年+", "10年+", "", ""]


def test_search_page_drops_sponsored():
    payload = {
        "data": [_row("ad", "1"), _row("abc", "0", appearDate="20261016", remoteWorkType=2)],
        "metadata": {"pagination": {"total": 9, "currentPage": 1, "lastPage": 3}},
    }
    out = shape.search_page(payload)
    assert [j["id"] for j in out["jobs"]] == ["abc"]
    assert out["jobs"][0]["posted"] == "2026-10-16"
    assert out["jobs"][0]["remote"] == "部分遠端"
    assert out["jobs"][0]["url"] == "https://www.104.com.tw/job/abc"
    assert (out["total"], out["pages"], out["has_next"]) == (9, 3, True)


def test_job_detail_tolerates_missing_parts():
    out = shape.job_detail({"data": {"header": {"custUrl": "https://www.104.com.tw/company/xyz"}}})
    assert out["company_id"] == "xyz" and out["requirements"]["skills"] == []


def test_company_none_for_empty_shell():
    assert shape.company({"data": {"custName": None, "custNo": "zzz"}}) is None
    assert shape.company({"data": {"custName": "ACME", "followerCount": "7"}})["followers"] == 7


def test_company_openings_default_salary():
    payload = {"data": {"list": {"topJobs": [], "normalJobs": [{"jobNo": "j1", "jobSalaryDesc": ""}]}}}
    assert shape.company_openings(payload)[0]["salary"] == "待遇面議"


class _Resp:
    def __init__(self, status, body=None):
        self.status_code, self._body = status, body

    def json(self):
        if self._body is None:
            raise ValueError("not json")
        return self._body


def _fake_send(monkeypatch, *statuses):
    calls = []

    def send(url, params, headers, profile, body=None):
        calls.append(profile)
        return _Resp(*statuses[len(calls) - 1])

    monkeypatch.setattr(http, "_send", send)
    monkeypatch.setattr(http, "DEFAULT_GAP", 0)
    monkeypatch.setattr(http, "RETRY_PAUSE", 0)
    return calls


def test_block_is_retried_with_second_fingerprint(monkeypatch):
    calls = _fake_send(monkeypatch, (403,), (200, {"ok": 1}))
    assert http.get_json("u", referer="r") == {"ok": 1}
    assert calls == ["chrome", "chrome124"]


def test_not_found_fails_fast(monkeypatch):
    calls = _fake_send(monkeypatch, (404,), (200, {}))
    with pytest.raises(http.SiteError, match="404"):
        http.get_json("u", referer="r")
    assert len(calls) == 1


def test_persistent_block_raises(monkeypatch):
    calls = _fake_send(monkeypatch, (403,), (403,), (429,), (403,))
    with pytest.raises(http.SiteError, match="403"):
        http.get_json("u", referer="r")
    assert len(calls) == 4  # two rounds over both profiles


def test_non_json_body_raises(monkeypatch):
    _fake_send(monkeypatch, (200, None))
    with pytest.raises(http.SiteError, match="JSON"):
        http.get_json("u", referer="r")


def test_block_that_clears_on_the_second_round_succeeds(monkeypatch):
    calls = _fake_send(monkeypatch, (403,), (403,), (200, {"ok": 1}))
    assert http.get_json("u", referer="r") == {"ok": 1}
    assert len(calls) == 3
