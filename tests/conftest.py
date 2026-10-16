import pytest

from tw_jobs_mcp import http


@pytest.fixture(autouse=True)
def fresh_cache():
    http.clear_cache()
    yield
    http.clear_cache()
