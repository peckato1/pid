import datetime
import logging
import os
import time

import requests

logger = logging.getLogger(__name__)

BASE_URL = "https://api.golemio.cz"
DEFAULT_TIMEOUT = 10


def _api_key() -> str:
    # Read lazily so importing this module doesn't require the env var
    # (tests, tooling, etc.).
    return os.environ["GOLEMIO_API_KEY"]


def _headers() -> dict[str, str]:
    return {"x-access-token": _api_key()}


def _until(seconds: float) -> str:
    return (datetime.datetime.now() + datetime.timedelta(seconds=seconds)).strftime("%H:%M:%S")


def _sleep_until_reset(headers) -> None:
    reset_ms = headers.get("x-ratelimit-reset")
    if not reset_ms:
        logger.info("rate limit hit, sleeping 1.00s (no reset header) (until %s)", _until(1))
        time.sleep(1)
        return
    try:
        wait = float(reset_ms) / 1000 - time.time()
    except ValueError:
        wait = 1
    if wait > 0:
        wait = min(wait + 0.05, 30)
        logger.info("rate limit hit, sleeping %.2fs (until %s)", wait, _until(wait))
        time.sleep(wait)


def get(path: str, *, timeout: float = DEFAULT_TIMEOUT) -> requests.Response:
    """GET an absolute path on the Golemio API.

    Honours x-ratelimit-reset on 429 and on responses where remaining quota
    is exhausted. Caller inspects status_code / .content / .json().
    """
    url = path if path.startswith("http") else f"{BASE_URL}{path}"
    r = requests.get(url, headers=_headers(), timeout=timeout)
    if r.status_code == 429:
        _sleep_until_reset(r.headers)
        r = requests.get(url, headers=_headers(), timeout=timeout)
    if r.headers.get("x-ratelimit-remaining") == "0":
        _sleep_until_reset(r.headers)
    return r
