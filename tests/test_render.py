"""The compact text the model reads, and the budget that keeps it compact."""
import asyncio
import json

from tw_jobs_mcp import render, server, service
from tw_jobs_mcp.j104 import api, shape


def _row(i, **extra):
    return {
        "jobName": f"職缺{i}|含直線", "custName": "ACME", "salaryLow": 60000, "salaryHigh": 80000, "s10": 50,
        "jobAddrNoDesc": "台北市", "optionEdu": [4, 5], "appearDate": "20261016", "jobType": "0",
        "pcSkills": [{"description": s} for s in "ABCDEFG"],
        "link": {"job": f"https://x/job/j{i}", "cust": "https://x/company/c"}, **extra,
    }


def _page(rows, total=40):
    return {"data": rows, "metadata": {"pagination": {"total": total, "currentPage": 1, "lastPage": 2}}}


def test_pay_formats():
    assert render.pay(None) == "面議"
    assert render.pay({"unit": "月薪", "min": 50000, "max": 60000}) == "月50000~60000"
    assert render.pay({"unit": "年薪", "min": 1000000, "max": None}) == "年1000000+"
    assert render.pay({"unit": "時薪", "min": None, "max": 300}) == "時~300"
    assert render.pay({"unit": "日薪", "min": 2500, "max": 2500}) == "日2500"


def test_search_table_shape(monkeypatch):
    monkeypatch.setattr(api, "search", lambda _: _page([_row(1), _row(2, remoteWorkType=1)]))
    text = server.search_jobs(keyword="x")
    lines = text.splitlines()
    assert lines[0] == "共 36 筆，第 1/2 頁"  # 40 minus the two paid rows on each of 2 pages
    assert lines[1].split("|") == ["id", "company_id", "職稱", "公司", "薪資", "地點", "學歷", "技能", "刊登"]
    cells = lines[2].split("|")
    assert len(cells) == 9 and cells[0] == "j1" and cells[1] == "c"
    assert cells[2] == "職缺1/含直線"  # a pipe in a title must not break the table
    assert cells[4] == "月60000~80000" and cells[6] == "大學~碩士"
    assert cells[7] == "A/B/C/D/E"  # at most five skills
    assert cells[8] == "10-16" and "（遠端）" in lines[3]


def test_empty_result_and_errors(monkeypatch):
    monkeypatch.setattr(api, "search", lambda _: _page([], total=0))
    monkeypatch.setattr(service, "_broaden", lambda *a: None)  # no live fallback in a unit test
    assert server.search_jobs(keyword="x").startswith("無結果（共 0 筆）")
    assert server.search_jobs(education="亂寫").startswith("錯誤：education")
    assert "台北市中山區" in server.search_jobs(area=["中山區"])


def test_json_mode_is_compact_and_complete(monkeypatch):
    monkeypatch.setenv("TW_JOBS_FORMAT", "json")
    monkeypatch.setattr(api, "search", lambda _: _page([_row(1)]))
    raw = server.search_jobs(keyword="x")
    assert ": " not in raw and ", " not in raw  # compact separators, no indentation
    assert chr(10) not in raw
    assert json.loads(raw)["jobs"][0]["pay"]["max"] == 80000


def test_long_text_is_clipped_unless_full(monkeypatch):
    detail = {"data": {"header": {"jobName": "T", "custUrl": "https://x/company/c"},
                       "jobDetail": {"jobDescription": "字" * 3000}}}
    monkeypatch.setattr(api, "job", lambda _: detail)
    short, full = server.get_job("j1"), server.get_job("j1", full=True)
    assert len(short) < 1800 and "full=True" in short
    assert len(full) > 3000 and "full=True" not in full


def test_company_text_lists_openings(monkeypatch):
    monkeypatch.setattr(api, "company", lambda _: {"data": {"custName": "ACME", "custNo": "abc", "empNo": "50人"}})
    monkeypatch.setattr(api, "company_jobs", lambda *_: {"data": {"list": {"normalJobs": [
        {"jobNo": "j1", "jobName": "工程師", "jobSalaryDesc": "月薪 5 萬", "jobAddrNoDesc": "台北"}]}}})
    text = server.get_company("abc", with_openings=True)
    assert text.startswith("ACME｜") and "j1|工程師|月薪 5 萬|台北|" in text
    assert server.get_company("abc").count("\n") == 1  # no openings block unless asked


def test_overview_text():
    out = render.overview({"matching_jobs": 99, "sampled": 10, "undisclosed_share": 0.4,
                           "by_unit": {"月薪": {"count": 6, "min": 1, "median": 2, "max": 3, "p25": 1, "p75": 3}}})
    assert out.splitlines() == ["符合 99 筆，取樣 10 筆，未公開薪資 40%", "月薪 n=6 最低 1 中位 2 最高 3 p25 1 p75 3"]


# ---- the budget ----------------------------------------------------------------

def test_a_full_page_of_results_stays_small(monkeypatch):
    monkeypatch.setattr(api, "search", lambda _: _page([_row(i) for i in range(20)]))
    text = server.search_jobs(keyword="x")
    as_json = json.dumps(service.search_jobs(keyword="x"), ensure_ascii=False, indent=2)
    assert len(text) < 120 * 20 + 100  # about 120 characters a job
    assert len(text) * 4 < len(as_json)


def test_tool_listing_stays_small():
    tools = asyncio.run(server.mcp.list_tools())
    size = sum(len(json.dumps(
        {"name": t.name, "description": t.description, "inputSchema": t.inputSchema},
        ensure_ascii=False, separators=(",", ":"))) for t in tools)
    assert size < 2900, size
    assert len(server.INSTRUCTIONS) < 900


def test_no_duplicate_structured_payload():
    """Clients that show both the text and structuredContent would pay twice."""
    assert all(t.outputSchema is None for t in asyncio.run(server.mcp.list_tools()))


def test_schema_has_no_titles_or_null_wrappers():
    for tool in asyncio.run(server.mcp.list_tools()):
        text = json.dumps(tool.inputSchema)
        assert '"title"' not in text and '"anyOf"' not in text
