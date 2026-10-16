"""Start the real server as a subprocess and talk to it the way an MCP client does.

No network access to 104 is needed: only tool discovery and offline tools are called.
"""
import asyncio
import socket
import subprocess
import sys
import time

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
try:
    from mcp.client.streamable_http import streamable_http_client as http_client
except ImportError:  # older mcp releases
    from mcp.client.streamable_http import streamablehttp_client as http_client

TOOLS = {"search_jobs", "get_job", "get_company", "salary_overview", "lookup_code", "sources"}


async def _inspect(session: ClientSession) -> None:
    await session.initialize()
    assert {t.name for t in (await session.list_tools()).tools} == TOOLS
    bad = await session.call_tool("search_jobs", {"education": "學士"})
    assert bad.isError  # the schema lists the valid values, so a wrong one never reaches the server
    result = await session.call_tool("lookup_code", {"kind": "area", "name": "大安"})
    assert "台北市大安區" in result.content[0].text
    result = await session.call_tool("search_jobs", {"per_page": 99})
    assert "per_page" in result.content[0].text  # validation error, no request sent


def test_stdio_transport():
    async def run():
        params = StdioServerParameters(command=sys.executable, args=["-m", "tw_jobs_mcp"])
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await _inspect(session)

    asyncio.run(run())


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def test_streamable_http_transport():
    port = _free_port()
    proc = subprocess.Popen(
        [sys.executable, "-m", "tw_jobs_mcp", "--transport", "streamable-http", "--port", str(port)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    try:
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            try:
                socket.create_connection(("127.0.0.1", port), timeout=0.5).close()
                break
            except OSError:
                time.sleep(0.2)
        else:
            pytest.fail("HTTP server did not start")

        async def run():
            async with http_client(f"http://127.0.0.1:{port}/mcp") as (read, write, _):
                async with ClientSession(read, write) as session:
                    await _inspect(session)

        asyncio.run(run())
    finally:
        proc.terminate()
        proc.wait(timeout=10)
