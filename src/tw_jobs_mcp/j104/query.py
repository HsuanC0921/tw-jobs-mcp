"""Validate tool arguments and turn them into 104 search parameters."""
from . import codes

SORTS = {"relevance": "15", "newest": "16", "salary": "13"}
JOB_TYPES = {"全職": "1", "兼職": "2", "高階": "3", "派遣": "4"}  # `ro`; 5 is HTTP 400
SALARY_UNITS = {"月薪": "M", "年薪": "Y", "日薪": "D", "時薪": "H"}  # without it scmin is ignored
EDUCATION = {"高中職": "2", "專科": "3", "大學": "4", "碩士": "5", "博士": "6"}
# `jobexp` only accepts these buckets: code -> years the posting asks for at least.
EXPERIENCE = {1: 0, 3: 1, 5: 3, 10: 5, 99: 10}
MAX_PAGE_SIZE = 30


class ArgError(ValueError):
    """A tool argument is unusable. The message tells the caller how to fix it."""


def _pick(label: str, value: str, table: dict[str, str]) -> str:
    if value not in table:
        raise ArgError(f"{label} 只能是 {'、'.join(table)}，收到 '{value}'")
    return table[value]


def check_paging(page: int, per_page: int) -> None:
    if page < 1:
        raise ArgError(f"page 必須 >= 1，收到 {page}")
    if not 1 <= per_page <= MAX_PAGE_SIZE:
        raise ArgError(f"per_page 必須介於 1 到 {MAX_PAGE_SIZE}，收到 {per_page}")


def _codes(kind: str, names) -> str | None:
    return ",".join(codes.resolve(kind, list(names))) if names else None


def build(
    *, keyword="", area=(), jobcat=(), salary_min=None, salary_unit="月薪",
    job_type=None, remote=False, new_only=False, my_years=None,
    education=None, sort="relevance", page=1, per_page=20, keyword_en=None, area_names=None,  # the last two are for other sources
) -> dict[str, str]:
    """Validate everything first, then emit only the parameters that were asked for."""
    check_paging(page, per_page)
    if my_years is not None and my_years < 0:
        raise ArgError(f"my_years 不可為負數，收到 {my_years}")

    has_salary = salary_min is not None
    wanted = [
        ("order", _pick("sort", sort, SORTS)),
        ("page", page),
        ("pagesize", per_page),
        ("keyword", keyword),
        ("kwop", "3" if keyword else None),  # title and company; 7 measured slightly worse
        ("area", _codes("area", area)),
        ("jobcat", _codes("jobcat", jobcat)),
        ("scmin", salary_min),
        ("sctp", _pick("salary_unit", salary_unit, SALARY_UNITS) if has_salary else None),
        ("scstrict", "1" if has_salary else None),
        ("ro", _pick("job_type", job_type, JOB_TYPES) if job_type else None),
        ("remoteWork", "1,2" if remote else None),  # 1 完全遠端、2 部分遠端
        ("isnew", "7" if new_only else None),
        ("jobexp", _experience(my_years)),
        ("edu", _pick("education", education, EDUCATION) if education else None),
    ]
    return {name: str(value) for name, value in wanted if value not in (None, "")}


def _experience(years: int | None) -> str | None:
    if years is None:
        return None
    return ",".join(str(code) for code, floor in EXPERIENCE.items() if floor <= years)
