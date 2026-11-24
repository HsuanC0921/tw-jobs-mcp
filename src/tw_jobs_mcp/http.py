"""The only module that touches the network.

104 sits behind Cloudflare, which turns plain HTTP clients away with a 403.
curl_cffi can send a real Chrome TLS fingerprint, which gets through.

Requests are paced per host, and responses are kept for a few minutes
(TW_JOBS_CACHE_TTL seconds, 0 turns it off) so an agent that re-reads the same
posting does not hit the site again.
"""
import json
import os
import threading
import time
from urllib.parse import urlsplit

from curl_cffi import requests

DEFAULT_GAP = 1.0  # seconds between requests to one host, to stay polite
HOST_GAP = {  # job-board APIs that exist to be read publicly can go faster
    "boards-api.greenhouse.io": 0.2,
    "api.lever.co": 0.2,
    "www.104.com.tw": 2.5,  # 104 starts answering 403 after a short burst, so go slower than the default
    "api.cake.me": 1.2,
    "freehire.me": 0.5,
}
PROFILES = ("chrome", "chrome124")
ROUNDS = 1  # one pass over the profiles; more retries during a block only deepen it
RETRY_PAUSE = 2.0
BLOCKED = {403, 429}
COOLDOWNS = (120.0, 300.0, 900.0)  # seconds a host is left alone after repeated blocks, per consecutive block
CACHE_TTL = float(os.environ.get("TW_JOBS_CACHE_TTL", "300"))
CACHE_SIZE = 256

_cool_lock = threading.Lock()
_cool_until: dict[str, float] = {}
_strikes: dict[str, int] = {}
_pace_lock = threading.Lock()
_next_slot: dict[str, float] = {}
_cache_lock = threading.Lock()
_cache: dict[str, tuple[float, object]] = {}


class SiteError(Exception):
    """A site refused, failed, or answered with something unusable."""


def clear_cache() -> None:
    with _cache_lock:
        _cache.clear()
    with _cool_lock:
        _cool_until.clear()
        _strikes.clear()


def _check_cooling(host: str) -> None:
    """A host that just blocked us is left alone for a while; hammering it only extends the block."""
    with _cool_lock:
        wait = _cool_until.get(host, 0.0) - time.monotonic()
    if wait > 0:
        raise SiteError(f"{host} 剛擋下請求，為避免加重限流暫停 {int(wait) + 1} 秒後再試")


def _note_block(host: str) -> None:
    with _cool_lock:
        strikes = _strikes.get(host, 0)
        _strikes[host] = strikes + 1
        _cool_until[host] = time.monotonic() + COOLDOWNS[min(strikes, len(COOLDOWNS) - 1)]


def _note_ok(host: str) -> None:
    with _cool_lock:
        _strikes.pop(host, None)


def _recall(key: str):
    with _cache_lock:
        entry = _cache.get(key)
        if entry and time.monotonic() - entry[0] < CACHE_TTL:
            return entry[1]
    return None


def _remember(key: str, value) -> None:
    if CACHE_TTL <= 0:
        return
    with _cache_lock:
        if len(_cache) >= CACHE_SIZE:
            _cache.pop(next(iter(_cache)))  # oldest first
        _cache[key] = (time.monotonic(), value)


def _pace(host: str) -> None:
    """Reserve the next free slot for this host, then wait for it outside the lock."""
    with _pace_lock:
        now = time.monotonic()
        slot = max(now, _next_slot.get(host, 0.0))
        _next_slot[host] = slot + HOST_GAP.get(host, DEFAULT_GAP)
    if slot > now:
        time.sleep(slot - now)


def _send(url: str, params, headers: dict, profile: str, body=None):
    if body is not None:
        return requests.post(url, json=body, headers=headers, impersonate=profile, timeout=20)
    return requests.get(url, params=params, headers=headers, impersonate=profile, timeout=20)


def _reason(status: int) -> str:
    if status in BLOCKED:
        return f"網站回應 HTTP {status}，可能被 Cloudflare 擋下或太頻繁"
    if status == 404:
        return "網站回應 HTTP 404，找不到這個編號"
    if status == 400:
        return "網站回應 HTTP 400，查詢參數不被接受"
    return f"網站回應 HTTP {status}"


def _fetch(url: str, params, headers: dict, body=None):
    host = urlsplit(url).netloc
    _check_cooling(host)
    failure = None
    for attempt, profile in enumerate(PROFILES * ROUNDS):
        if attempt >= len(PROFILES):
            time.sleep(RETRY_PAUSE)
        _pace(host)
        try:
            resp = _send(url, params, headers, profile, body)
        except Exception as exc:
            failure = SiteError(f"連線失敗：{exc}")
            continue
        if resp.status_code == 200:
            _note_ok(host)
            return resp
        failure = SiteError(_reason(resp.status_code))
        if resp.status_code not in BLOCKED:
            raise failure  # another fingerprint only helps against a block
    _note_block(host)
    raise failure


def _cached(kind: str, url: str, params, referer: str | None, accept: str, parse, body=None, extra=None):
    key = json.dumps([kind, url, params, body], sort_keys=True, default=str)
    if (hit := _recall(key)) is not None:
        return hit
    headers = {"Accept": accept, "Accept-Language": "zh-TW,zh;q=0.9"}
    if referer:
        headers["Referer"] = referer
    headers.update(extra or {})
    value = parse(_fetch(url, params, headers, body))
    _remember(key, value)
    return value


def _json_body(resp) -> dict:
    try:
        return resp.json()
    except ValueError as exc:
        raise SiteError("網站回傳的內容不是 JSON") from exc


def get_json(url: str, *, referer: str | None = None, params=None, headers: dict | None = None):
    return _cached("json", url, params, referer, "application/json, text/plain, */*", _json_body, extra=headers)


def post_json(url: str, body: dict, *, referer: str | None = None, headers: dict | None = None):
    return _cached("post", url, None, referer, "application/json", _json_body, body, extra=headers)


def get_text(url: str, *, referer: str | None = None, params=None) -> str:
    return _cached("text", url, params, referer, "text/html,*/*", lambda resp: resp.text)
