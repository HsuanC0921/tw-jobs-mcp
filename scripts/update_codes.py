"""Download 104's public category trees and flatten them to {code: name}.

    uv run python scripts/update_codes.py
"""
import json
from pathlib import Path

from curl_cffi import requests

SOURCES = {
    "jobcat": "https://static.104.com.tw/category-tool/json/JobCat.json",
    "area": "https://static.104.com.tw/category-tool/json/Area.json",
}
OUT = Path(__file__).resolve().parents[1] / "src" / "tw_jobs_mcp" / "j104" / "data"


def flatten(nodes, into):
    for node in nodes:
        into[node["no"]] = node["des"]
        flatten(node.get("n") or [], into)
    return into


for kind, url in SOURCES.items():
    resp = requests.get(url, impersonate="chrome", timeout=30)
    resp.raise_for_status()
    flat = flatten(resp.json(), {})
    (OUT / f"{kind}.json").write_text(
        json.dumps(flat, ensure_ascii=False, indent=0, sort_keys=True), encoding="utf-8"
    )
    print(kind, len(flat))
