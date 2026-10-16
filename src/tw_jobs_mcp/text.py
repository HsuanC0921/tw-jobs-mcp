"""Small helpers for the HTML that other sites hand back."""
import html
import json
import re

_BREAKS = re.compile(r"(?i)<br\s*/?>|</(p|div|li|h[1-6]|tr|ul|ol)>")
_TAGS = re.compile(r"<[^>]+>")


def strip_html(raw: str) -> str:
    """HTML (possibly escaped twice, as Greenhouse sends it) to plain paragraphs."""
    if "&lt;" in raw:
        raw = html.unescape(raw)
    text = html.unescape(_TAGS.sub("", _BREAKS.sub("\n", raw)))
    text = re.sub(r"[ \t ]+", " ", text)
    return re.sub(r"\n\s*\n+", "\n", text).strip()


def json_ld(page: str, kind: str) -> dict:
    """The first schema.org block of the given @type in a page, or {}."""
    for block in re.findall(r'<script type="application/ld\+json">(.*?)</script>', page, re.S):
        try:
            data = json.loads(block)
        except ValueError:
            continue
        if isinstance(data, dict) and data.get("@type") == kind:
            return data
    return {}
