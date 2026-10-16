"""What a capable agent still cannot know from the schema alone.

The schema pins every enumerated value, and the agent translates wording itself. What is left is
data the agent cannot see: whether a place name is ambiguous in 104's tables, how far a limit
reaches, and whether a search that came back empty has a looser form that does not. Each
assumption is reported in a note.
"""
from .j104 import codes, query

_RELAX = ("new_only", "remote", "my_years", "job_type", "education", "salary_min")
_MAX_WIDEN = 6  # a name matching more places or jobs than this is too vague to widen


def _widen(kind: str, name: str, notes: list[str]) -> tuple[list[str], bool]:
    """(codes, matched). Unique names pass through; a few close matches are all used."""
    try:
        return codes.resolve(kind, [name]), True
    except codes.AmbiguousName:
        hits = codes.search(kind, name, limit=50)
        exact = [h for h in hits if h[1] in (name, name + "市", name + "縣", name + "縣市")]
        hits = exact or hits  # "新竹" means 新竹市 and 新竹縣市, not every town inside them
        if 0 < len(hits) <= _MAX_WIDEN:
            notes.append(f"{kind} '{name}' 對應多個，已全部納入：" + "、".join(n for _, n in hits))
            return [c for c, _ in hits], True
        return [], False


def normalize(f: dict) -> tuple[dict, list[str]]:
    """A copy of the search filters with loose values repaired, and notes on every repair."""
    f, notes = dict(f), []
    if f.get("per_page", 20) > query.MAX_PAGE_SIZE or f.get("per_page", 20) < 1:
        f["per_page"] = min(max(f.get("per_page", 20), 1), query.MAX_PAGE_SIZE)
        notes.append(f"per_page 已調整為 {f['per_page']}（上限 {query.MAX_PAGE_SIZE}）")
    if f.get("page", 1) < 1:
        f["page"] = 1
    if (f.get("my_years") or 0) < 0:
        f["my_years"] = 0
    f["area_names"] = tuple(f.get("area") or ())  # the other sources match on names, not 104 codes
    for kind in ("area", "jobcat"):
        resolved = []
        for name in f.get(kind) or ():
            found, matched = _widen(kind, name, notes)
            resolved += found
            if not matched and kind == "jobcat":
                f["keyword"] = f"{f.get('keyword', '')} {name}".strip()
                notes.append(f"職類 '{name}' 對應不到，改當關鍵字搜尋")
            elif not matched:
                notes.append(f"地區 '{name}' 對應不到，已不限地區；可用 lookup_code 查名稱")
        f[kind] = tuple(dict.fromkeys(resolved))
    return f, notes


def relaxations(f: dict):
    """Yield (looser filters, what was dropped), dropping one more optional filter each time."""
    f = dict(f)
    dropped = []
    for field in _RELAX:
        if f.get(field) not in (None, False, "", ()):
            f[field] = False if field in ("new_only", "remote") else None
            dropped.append(field)
            yield dict(f), list(dropped)
