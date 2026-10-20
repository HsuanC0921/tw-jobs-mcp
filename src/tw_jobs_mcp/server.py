"""MCP tools. Replies are compact text, to keep the model's context small.

Set TW_JOBS_FORMAT=json to get the full structured data as compact JSON instead.
"""
import argparse
import json
import os

from typing import Literal

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from . import __version__, render, service

INSTRUCTIONS = (
    "台灣求職查詢（唯讀）。你負責把使用者的白話需求轉成精確參數，不要把原句當關鍵字。\n"
    "來源：104 最大、條件最完整（中文）；yourator 新創與外商據點；boards、workday 是外商官網職缺（英文，只支援 keyword 與 area）；all 全部合併。外商、英文、稀有缺用 all。\n"
    "關鍵字：職稱或技能各準備中文（keyword，給 104）與英文（keyword_en，給其他來源）兩種常用說法，互為翻譯，1~3 個短詞，不放地區與薪資。\n"
    "條件：填成使用者真正的限制，單位自行換算（年薪百萬 → salary_min=1000000, salary_unit=年薪）。\n"
    "結果下方的「註」是伺服器做的假設或放寬，請轉告使用者；無結果時先看註再自行調整。總筆數遠多於一頁時，說明只看了這一頁，需要再用 page 翻。流程 search_jobs → get_job → get_company，id 原樣傳入。連不上時呼叫 sources。"
)

mcp = FastMCP("tw-jobs", instructions=INSTRUCTIONS)
Education = Literal["高中職", "專科", "大學", "碩士", "博士"]
JobType = Literal["全職", "兼職", "高階", "派遣"]
SalaryUnit = Literal["月薪", "年薪", "日薪", "時薪"]
Sort = Literal["relevance", "newest", "salary"]
Source = Literal["104", "yourator", "boards", "workday", "all"]
READ_ONLY = ToolAnnotations(
    readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=True
)


def _emit(result: dict, as_text) -> str:
    as_json = os.environ.get("TW_JOBS_FORMAT", "text") == "json"
    if as_json:
        return json.dumps(result, ensure_ascii=False, separators=(",", ":"))
    return render.failure(result) if "error" in result else as_text(result)


def _tool(fn):
    return mcp.tool(annotations=READ_ONLY, structured_output=False)(fn)


@_tool
def search_jobs(
    keyword: str = "",
    keyword_en: str = "",
    source: Source = "104",
    salary_min: int | None = None,
    salary_unit: SalaryUnit = "月薪",
    include_negotiable: bool = False,
    area: list[str] | None = None,
    jobcat: list[str] | None = None,
    education: Education | None = None,
    my_years: int | None = None,
    job_type: JobType | None = None,
    remote_only: bool = False,
    new_only: bool = False,
    sort: Sort = "relevance",
    page: int = 1,
    per_page: int = 20,
) -> str:
    """搜尋職缺，回傳表格（id 給 get_job，company_id 給 get_company）。
keyword 中文（給 104）、keyword_en 英文（給其他來源），互為翻譯；只填一個時兩邊共用。
非 104 來源只支援 keyword、area（yourator 另有 sort=newest，boards 另有 remote_only），其餘條件會在註記說明未套用。
area/jobcat 填中文名稱（台北市、軟體工程師）。salary_min 的單位是 salary_unit，104 預設不含面議，include_negotiable=True 才納入。
my_years＝使用者的年資，列出要求不超過它的（含經驗不拘）。per_page≤30，用 page 翻頁。"""
    result = service.search_jobs(
        keyword=keyword, keyword_en=keyword_en, source=source, salary_min=salary_min, salary_unit=salary_unit,
        include_negotiable=include_negotiable, area=area or (),
        jobcat=jobcat or (), education=education, my_years=my_years, job_type=job_type,
        remote=remote_only, new_only=new_only, sort=sort, page=page, per_page=per_page,
    )
    return _emit(result, render.search)


@_tool
def get_job(job_id: str, full: bool = False, applicants: bool = False, similar: bool = False) -> str:
    """職缺完整內容，full=True 看全文。104 限定：applicants＝近兩週應徵者人數與背景，similar＝相似職缺。"""
    return _emit(service.get_job(job_id, applicants, similar), lambda d: render.job(d, full))


@_tool
def get_company(company_id: str, with_openings: bool = False, keyword: str = "", full: bool = False) -> str:
    """公司簡介。with_openings=True 附目前職缺；keyword 只列符合的職缺（104 連內文比對）。"""
    return _emit(service.get_company(company_id, with_openings, keyword), lambda d: render.company(d, full))


@_tool
def salary_overview(
    keyword: str = "",
    area: list[str] | None = None,
    jobcat: list[str] | None = None,
    education: Education | None = None,
    my_years: int | None = None,
    job_type: JobType | None = None,
    remote_only: bool = False,
    new_only: bool = False,
    pages: int = 3,
) -> str:
    """薪資行情：取前 pages（1~5）頁有公開薪資的職缺，依單位統計筆數、最低、四分位、中位、最高。
    參數同 search_jobs。樣本統計，非全站。"""
    result = service.salary_overview(
        keyword=keyword, area=area or (), jobcat=jobcat or (), education=education,
        my_years=my_years, job_type=job_type, remote=remote_only, new_only=new_only, pages=pages,
    )
    return _emit(result, render.overview)


@_tool
def sources() -> str:
    """即時檢查 104、Yourator 與各外商職缺板目前哪些連得上，哪些被擋。"""
    return _emit(service.source_status(), render.status)


@_tool
def lookup_code(kind: str, name: str = "", parent: str = "") -> str:
    """查地區（area）或職類（jobcat）代碼。name 留空則列 parent 的下一層（parent 也空＝最上層）。"""
    return _emit(service.lookup_code(kind, name, parent), lambda d: render.codes(d["matches"]))


def _slim(node):
    """Drop schema noise the model does not need: titles, and `anyOf [X, null]` wrappers."""
    if isinstance(node, dict):
        if isinstance(node.get("title"), str):
            del node["title"]
        kinds = node.get("anyOf")
        if kinds and len(rest := [k for k in kinds if k.get("type") != "null"]) == 1:
            del node["anyOf"]
            node.update(rest[0])
            if node.get("default") is None:
                node.pop("default", None)
        for value in node.values():
            _slim(value)
    elif isinstance(node, list):
        for value in node:
            _slim(value)


for _registered in mcp._tool_manager.list_tools():
    _slim(_registered.parameters)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="tw-jobs-mcp",
        description="MCP server for Taiwan job boards (104). Default transport is stdio.",
    )
    parser.add_argument(
        "--transport", choices=("stdio", "streamable-http"),
        default=os.environ.get("TW_JOBS_TRANSPORT", "stdio"),
    )
    parser.add_argument("--host", default=os.environ.get("TW_JOBS_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("TW_JOBS_PORT", "8000")))
    parser.add_argument("--version", action="version", version=f"tw-jobs-mcp {__version__}")
    args = parser.parse_args(argv)
    mcp.settings.host, mcp.settings.port = args.host, args.port
    mcp.run(transport=args.transport)


if __name__ == "__main__":
    main()
