"""Cache, code browsing, statistics, richer rows, CLI and MCP surface."""
import asyncio
import json

import pytest

from tw_jobs_mcp import server, service
from tw_jobs_mcp import http
from tw_jobs_mcp.j104 import api, codes, shape, stats


# ---- cache -------------------------------------------------------------------

def _count_calls(monkeypatch):
    calls = []

    def send(url, params, headers, profile, body=None):
        calls.append(url)

        class Resp:
            status_code = 200

            def json(self):
                return {"n": len(calls)}

        return Resp()

    monkeypatch.setattr(http, "_send", send)
    monkeypatch.setattr(http, "DEFAULT_GAP", 0)
    return calls


def test_same_request_is_served_from_cache(monkeypatch):
    calls = _count_calls(monkeypatch)
    first = http.get_json("u", referer="r", params={"a": "1"})
    assert http.get_json("u", referer="r", params={"a": "1"}) == first
    assert len(calls) == 1
    http.get_json("u", referer="r", params={"a": "2"})
    assert len(calls) == 2


def test_cache_can_be_disabled(monkeypatch):
    calls = _count_calls(monkeypatch)
    monkeypatch.setattr(http, "CACHE_TTL", 0)
    http.get_json("u", referer="r")
    http.get_json("u", referer="r")
    assert len(calls) == 2


def test_cache_drops_oldest_when_full(monkeypatch):
    calls = _count_calls(monkeypatch)
    monkeypatch.setattr(http, "CACHE_SIZE", 2)
    for name in ("a", "b", "c"):
        http.get_json(name, referer="r")
    http.get_json("a", referer="r")  # evicted, so fetched again
    assert len(calls) == 4


# ---- code browsing -----------------------------------------------------------

def test_roots_groups_and_items_form_a_tree():
    roots = codes.children("jobcat")
    assert len(roots) == 18 and all(c.endswith("000000") for c, _ in roots)
    software = dict(roots)["2007000000"]
    groups = codes.children("jobcat", "2007000000")
    assert groups and all(c.startswith("2007") and c.endswith("000") for c, _ in groups), software
    items = codes.children("jobcat", groups[0][0])
    assert items and all(c.startswith(groups[0][0][:7]) and not c.endswith("000") for c, _ in items)


def test_city_lists_its_districts():
    names = [n for _, n in codes.children("area", "6001001000")]
    assert "台北市大安區" in names and "台北市" not in names


def test_item_has_no_children_and_bad_code_is_rejected():
    assert codes.children("area", "6001001005") == []
    with pytest.raises(ValueError):
        codes.children("area", "abc")


def test_every_code_is_reachable_from_a_root():
    for kind in codes.KINDS:
        seen = set(c for c, _ in codes.children(kind))
        for root in list(seen):
            for group, _ in codes.children(kind, root):
                seen.add(group)
                seen.update(c for c, _ in codes.children(kind, group))
        assert seen == set(codes.table(kind))


# ---- statistics --------------------------------------------------------------

def _job(unit=None, low=None, high=None):
    return {"pay": None if unit is None else {"unit": unit, "min": low, "max": high}}


def test_summary_groups_by_unit_and_uses_midpoints():
    jobs = [_job("月薪", 40000, 60000), _job("月薪", 50000, 50000), _job("月薪", 70000, None),
            _job("月薪", None, 30000), _job("年薪", 1_000_000, 1_400_000), _job()]
    out = stats.summarize(jobs)
    month = out["by_unit"]["月薪"]
    assert (month["count"], month["min"], month["max"]) == (4, 30000, 70000)
    assert month["median"] == 50000 and "p25" in month and "p75" in month
    assert out["by_unit"]["年薪"] == {"count": 1, "min": 1_200_000, "median": 1_200_000, "max": 1_200_000}
    assert out["sampled"] == 6 and out["undisclosed_share"] == 0.17


def test_summary_of_nothing():
    assert stats.summarize([]) == {"sampled": 0, "undisclosed_share": 0, "by_unit": {}}


# ---- richer rows -------------------------------------------------------------

def test_search_row_carries_company_and_requirements():
    row = shape.search_row({
        "jobName": "後端", "custName": "ACME", "salaryLow": 60000, "salaryHigh": 80000, "s10": 50,
        "link": {"job": "https://www.104.com.tw/job/abc", "cust": "https://www.104.com.tw/company/xyz"},
        "optionEdu": [4, 5, 99], "pcSkills": [{"code": "1", "description": "Python"}],
        "coIndustryDesc": "軟體業", "employeeCount": 50, "mrtDesc": "捷運南港站", "d3": "09:00~18:00",
    })
    assert row["company_id"] == "xyz" and row["id"] == "abc"
    assert row["education"] == ["大學", "碩士"] and row["skills"] == ["Python"]
    assert row["pay"] == {"unit": "月薪", "min": 60000, "max": 80000}
    assert (row["industry"], row["company_size"], row["nearby_mrt"], row["hours"]) == (
        "軟體業", 50, "捷運南港站", "09:00~18:00")


def test_negotiable_row_has_no_pay():
    assert shape.search_row({"s10": 10, "salaryLow": 0, "salaryHigh": 9_999_999})["pay"] is None


def test_job_detail_extra_fields():
    out = shape.job_detail({"data": {
        "industry": "軟體業", "employees": "50人", "closeDate": "2026/12/31",
        "jobDetail": {
            "jobCategory": [{"description": "後端工程師"}], "needEmp": "2人", "businessTrip": "無",
            "startWorkingDay": "一個月內", "vacationPolicy": "週休二日",
            "workPeriod": {"shifts": {"日班": []}, "note": "09:00~18:00"},
        },
        "condition": {"certificate": [{"description": "PMP"}]},
    }})
    assert out["categories"] == ["後端工程師"] and out["closes"] == "2026/12/31"
    assert out["conditions"]["shifts"] == ["日班"] and out["conditions"]["hours"] == "09:00~18:00"
    assert out["requirements"]["certificates"] == ["PMP"]


# ---- tools -------------------------------------------------------------------

def _row(i, low, high, kind=50):
    return {"jobName": f"j{i}", "jobType": "0", "salaryLow": low, "salaryHigh": high, "s10": kind,
            "link": {"job": f"https://x/job/j{i}", "cust": "https://x/company/c"}}


def test_salary_overview_pages_through_results(monkeypatch):
    pages = []

    def fake(params):
        pages.append(params["page"])
        rows = [_row(i, 40000 + 1000 * i, 50000 + 1000 * i) for i in range(4)]
        return {"data": rows, "metadata": {"pagination": {"total": 99, "currentPage": int(params["page"]), "lastPage": 2}}}

    monkeypatch.setattr(api, "search", fake)
    out = service.salary_overview(keyword="python", pages=5)
    assert pages == ["1", "2"]  # stops at the last page
    assert out["matching_jobs"] == 99 and out["by_unit"]["月薪"]["count"] == 8


def test_salary_overview_validates(monkeypatch):
    assert "pages" in service.salary_overview(pages=0)["error"]
    assert "education" in service.salary_overview(education="亂寫")["error"]


def test_lookup_code_browsing():
    assert len(service.lookup_code("jobcat")["matches"]) == 18
    assert service.lookup_code("area", parent="6001001000")["matches"]
    assert "error" in service.lookup_code("area", parent="oops")


# ---- MCP surface and CLI -----------------------------------------------------

def test_tools_are_read_only_and_described():
    tools = asyncio.run(server.mcp.list_tools())
    assert {t.name for t in tools} == {
        "search_jobs", "get_job", "get_company", "salary_overview", "lookup_code", "sources"}
    for tool in tools:
        assert tool.annotations.readOnlyHint is True and tool.annotations.destructiveHint is False
        assert tool.description


def test_tool_schemas_are_plain_json_schema():
    """Some clients choke on $ref/$defs or tuple-style schemas, so keep them flat."""
    for tool in asyncio.run(server.mcp.list_tools()):
        text = json.dumps(tool.inputSchema)
        assert "$ref" not in text and "$defs" not in text and "prefixItems" not in text
        assert tool.inputSchema["type"] == "object"
        required = {"get_job": ["job_id"], "get_company": ["company_id"], "lookup_code": ["kind"]}
        assert tool.inputSchema.get("required", []) == required.get(tool.name, [])


def test_cli_sets_host_port_and_transport(monkeypatch):
    seen = {}
    monkeypatch.setattr(server.mcp, "run", lambda transport: seen.update(transport=transport))
    server.main(["--transport", "streamable-http", "--host", "0.0.0.0", "--port", "9001"])
    assert seen["transport"] == "streamable-http"
    assert (server.mcp.settings.host, server.mcp.settings.port) == ("0.0.0.0", 9001)


def test_cli_defaults_to_stdio(monkeypatch):
    seen = {}
    monkeypatch.setattr(server.mcp, "run", lambda transport: seen.update(transport=transport))
    monkeypatch.delenv("TW_JOBS_TRANSPORT", raising=False)
    server.main([])
    assert seen["transport"] == "stdio"


def test_version_is_the_same_everywhere():
    import tomllib
    from pathlib import Path

    from tw_jobs_mcp import __version__

    root = Path(__file__).resolve().parents[1]
    assert tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"] == __version__
    assert json.loads((root / "manifest.json").read_text(encoding="utf-8"))["version"] == __version__
    assert __version__.split(".")[0] == "1"
