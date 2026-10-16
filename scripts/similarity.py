"""Measure how much of one Python tree appears in another.

    uv run python scripts/similarity.py MINE_DIR OTHER_DIR

Both trees are tokenized (comments and layout dropped, long strings collapsed) and
compared as overlapping token windows. Three numbers, each with a pass line:

  raw     share of my 12-token windows found in the other tree, names kept   <= 5%
  run     longest identical token run between any pair of files               <= 30
  shape   same share after renaming every identifier/string/number            <= 20%

`raw` catches copied code, `run` catches a single lifted block, `shape` catches code
that was only renamed. Some overlap is unavoidable when two programs talk to the same
API (parameter names, JSON keys), which is why the lines are not zero. Exit code 1 if
any line is crossed.
"""
import difflib
import io
import keyword
import sys
import tokenize
from pathlib import Path

WINDOW = 12
LIMITS = {"raw": 0.05, "run": 30, "shape": 0.20}
SKIP = {tokenize.COMMENT, tokenize.NL, tokenize.NEWLINE, tokenize.INDENT, tokenize.DEDENT,
        tokenize.ENCODING, tokenize.ENDMARKER}
FIXED = set(keyword.kwlist) | {"self", "None", "True", "False"}


def tokens(path: Path, anonymize: bool) -> list[str]:
    out = []
    for tok in tokenize.generate_tokens(io.StringIO(path.read_text(encoding="utf-8")).readline):
        if tok.type in SKIP:
            continue
        text = tok.string
        if anonymize:
            if tok.type == tokenize.NAME and text not in FIXED:
                text = "ID"
            elif tok.type == tokenize.STRING:
                text = "S"
            elif tok.type == tokenize.NUMBER:
                text = "N"
        elif tok.type == tokenize.STRING and len(text) > 60:
            text = "S"
        out.append(text)
    return out


def load(root: str, anonymize: bool) -> list[list[str]]:
    files = [p for p in Path(root).rglob("*.py") if ".venv" not in p.parts]
    return [t for t in (tokens(p, anonymize) for p in files) if len(t) > WINDOW]


def windows(seqs: list[list[str]]) -> set[tuple]:
    return {tuple(s[i:i + WINDOW]) for s in seqs for i in range(len(s) - WINDOW + 1)}


def share(mine: list[list[str]], other: list[list[str]]) -> float:
    ours, theirs = windows(mine), windows(other)
    return len(ours & theirs) / len(ours) if ours else 0.0


def longest_run(mine: list[list[str]], other: list[list[str]]) -> int:
    best = 0
    for a in mine:
        for b in other:
            match = difflib.SequenceMatcher(None, a, b, autojunk=False).find_longest_match(
                0, len(a), 0, len(b))
            best = max(best, match.size)
    return best


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__)
        return 2
    mine, other = sys.argv[1:]
    raw_a, raw_b = load(mine, False), load(other, False)
    shape_a, shape_b = load(mine, True), load(other, True)
    result = {
        "raw": share(raw_a, raw_b),
        "run": longest_run(raw_a, raw_b),
        "shape": share(shape_a, shape_b),
    }
    failed = False
    for name, value in result.items():
        over = value > LIMITS[name]
        failed |= over
        shown = f"{value:.1%}" if name != "run" else f"{value} tokens"
        limit = f"{LIMITS[name]:.0%}" if name != "run" else f"{LIMITS[name]} tokens"
        print(f"{name:5s} {shown:>12s}   limit {limit:>10s}   {'OVER' if over else 'ok'}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
