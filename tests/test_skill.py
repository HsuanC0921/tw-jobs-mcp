"""The agent skill and plugin files ship with the repository and stay in step with the package."""
import json
import re
from pathlib import Path

from tw_jobs_mcp import __version__

ROOT = Path(__file__).resolve().parent.parent


def test_skill_follows_the_agent_skills_format():
    skill = ROOT / "skills" / "tw-jobs" / "SKILL.md"
    head = re.match(r"---\n(.*?)\n---\n", skill.read_text(encoding="utf-8"), re.S).group(1)
    fields = dict(line.split(": ", 1) for line in head.splitlines())
    assert fields["name"] == skill.parent.name and re.fullmatch(r"[a-z0-9-]{1,64}", fields["name"])
    assert 0 < len(fields["description"]) <= 1024
    assert (skill.parent / "references" / "parameters.md").exists()


def test_skill_names_only_real_tools_and_arguments():
    import asyncio

    from tw_jobs_mcp import server

    text = (ROOT / "skills" / "tw-jobs" / "SKILL.md").read_text(encoding="utf-8")
    tools = {t.name: t for t in asyncio.run(server.mcp.list_tools())}
    for name in set(re.findall(r"`(search_jobs|get_job|get_company|salary_overview|lookup_code|sources)`", text)):
        assert name in tools
    arguments = set(tools["search_jobs"].inputSchema["properties"])
    for argument in re.findall(r"`(keyword_en|salary_unit|salary_min|my_years|remote_only|new_only|education|job_type|area)", text):
        assert argument in arguments


def test_plugin_files_match_the_package_version():
    plugin = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    assert plugin["version"] == __version__
    mcp = json.loads((ROOT / ".mcp.json").read_text(encoding="utf-8"))["mcpServers"]["tw-jobs"]
    assert mcp["args"][-1] == "tw-jobs-mcp"
    market = json.loads((ROOT / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
    assert market["plugins"][0]["name"] == plugin["name"]


def test_registry_entry_matches_the_package():
    entry = json.loads((ROOT / "server.json").read_text(encoding="utf-8"))
    assert entry["version"] == __version__ and entry["packages"][0]["version"] == __version__
    assert entry["packages"][0]["identifier"] == "tw-jobs-mcp" and len(entry["description"]) <= 100
    assert re.fullmatch(r"io\.github\.[A-Za-z0-9-]+/[a-zA-Z0-9._-]+", entry["name"])
    # the registry proves ownership by finding this exact line in the README shown on PyPI
    assert f"mcp-name: {entry['name']}" in (ROOT / "README.md").read_text(encoding="utf-8")
