"""Name <-> code lookup over 104's area and job-category trees (flat JSON).

Codes are ten digits in three groups, XXXX GGG SSS, and the tree follows the groups:
XXXX000000 is a root, XXXXGGG000 a group under it, XXXXGGGSSS an item under that.
"""
import json
import re
from functools import cache
from pathlib import Path

_DATA = Path(__file__).parent / "data"
KINDS = ("area", "jobcat")


class AmbiguousName(ValueError):
    """The name matched nothing, or too many things. `options` are close matches."""

    def __init__(self, kind: str, query: str, options: list[tuple[str, str]]):
        self.options = options
        shown = "、".join(f"{name}（{code}）" for code, name in options)
        super().__init__(
            f"{kind} '{query}' 無法唯一對應，"
            + (f"可能是：{shown}" if options else "找不到相近的名稱，請用中文名稱（不接受英文），或用 lookup_code 查")
        )


@cache
def _entries(kind: str) -> tuple[tuple[str, str], ...]:
    raw = json.loads((_DATA / f"{kind}.json").read_text(encoding="utf-8"))
    return tuple(raw.items())


def table(kind: str) -> dict[str, str]:
    return dict(_entries(kind))


def search(kind: str, query: str, limit: int = 8) -> list[tuple[str, str]]:
    """(code, name) pairs: exact names first, then prefixes, then substrings."""
    q = query.strip()
    if not q:
        return []
    ranked = []
    for code, name in _entries(kind):
        if name == q:
            tier = 0
        elif name.startswith(q):
            tier = 1
        elif q in name:
            tier = 2
        else:
            continue
        ranked.append((tier, len(name), code, name))
    ranked.sort()
    return [(code, name) for _, _, code, name in ranked[:limit]]


def children(kind: str, parent: str | None = None) -> list[tuple[str, str]]:
    """Direct children of a code, or the roots when `parent` is empty."""
    if not parent:
        return [(c, n) for c, n in _entries(kind) if c.endswith("000000")]
    if not re.fullmatch(r"\d{10}", parent):
        raise ValueError(f"代碼應為 10 位數字，收到 '{parent}'")
    if parent.endswith("000000"):
        head, step = parent[:4], lambda c: c[4:7] != "000" and c.endswith("000")
    elif parent.endswith("000"):
        head, step = parent[:7], lambda c: not c.endswith("000")
    else:
        return []  # an item has nothing below it
    return [(c, n) for c, n in _entries(kind) if c.startswith(head) and step(c)]


def resolve(kind: str, names: list[str]) -> list[str]:
    """Turn names (or ready-made codes) into 104 codes, or raise AmbiguousName."""
    known = table(kind)
    out = []
    for name in names:
        name = name.strip()
        if re.fullmatch(r"\d{10}", name) and name in known:
            out.append(name)
            continue
        hits = search(kind, name, limit=50)
        exact = [h for h in hits if h[1] in (name, name + "市", name + "縣", name + "縣市")]  # "新北" means 新北市
        pick = exact if exact else hits
        if len(pick) != 1:
            raise AmbiguousName(kind, name, pick[:8])
        out.append(pick[0][0])
    return out
