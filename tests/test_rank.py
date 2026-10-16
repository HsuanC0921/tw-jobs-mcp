from tw_jobs_mcp import service
from tw_jobs_mcp.j104 import api, rank


def _job(title, company="某公司"):
    return {"title": title, "company": company}


def test_rerank_puts_the_best_cover_first_and_is_stable():
    jobs = [_job("專案經理", "甲公司"), _job("【甲公司人才培育計畫】軟體開發", "甲集團"), _job("業務助理", "甲公司")]
    out = rank.rerank("甲公司 人才培育計畫", jobs)
    assert "培育計畫" in out[0]["title"]
    assert [j["title"] for j in out[1:]] == ["專案經理", "業務助理"]  # ties keep the original order


def _fake_104(pages):
    seen = []

    def search(params):
        seen.append(params)
        n = int(params["page"])
        rows = [{"jobName": f"p{n}-{i}", "custName": "C", "jobType": "1" if i < 2 else "0",
                 "link": {"job": f"https://x/job/{n}-{i}"}} for i in range(30)]
        return {"data": rows, "metadata": {"pagination": {"total": 30 * pages, "currentPage": n, "lastPage": pages}}}

    return search, seen


def test_ranked_search_pages_in_blocks_of_real_rows(monkeypatch):
    search, seen = _fake_104(4)
    monkeypatch.setattr(api, "search", search)
    out = service.search_jobs(keyword="p", per_page=20, page=2)
    # rows 20..39 of the 28-per-block stream: the end of block 1 and the start of block 2
    assert [p["page"] for p in seen] == ["1", "2"] and all(p["pagesize"] == "30" for p in seen)
    assert len(out["jobs"]) == 20 and out["total"] == 112 and out["pages"] == 6 and out["has_next"]
    assert out["jobs"][0]["id"] == "1-22"


def test_other_sorts_keep_the_plain_api_paging(monkeypatch):
    search, seen = _fake_104(2)
    monkeypatch.setattr(api, "search", search)
    service.search_jobs(keyword="p", sort="newest", per_page=10)
    assert seen[0]["pagesize"] == "10" and seen[0]["order"] == "16"


def test_other_sources_receive_place_names_not_104_codes(monkeypatch):
    from tw_jobs_mcp import yourator
    seen = {}
    monkeypatch.setattr(api, "search", lambda p: {"data": [], "metadata": {"pagination": {"total": 0}}})
    monkeypatch.setattr(yourator, "search", lambda **kw: seen.update(kw) or {"total": 0, "page": 1, "pages": 1, "has_next": False, "jobs": []})
    service._search_one("yourator", {"area": ("6001006001",), "area_names": ("新竹",), "keyword": "x"}, 5)
    assert seen["areas"] == ["新竹"]
    assert yourator.area_codes(["新竹", "台北市大安區"]) == ["TPE", "HSZ", "HSQ"]  # bare 新竹 covers both
