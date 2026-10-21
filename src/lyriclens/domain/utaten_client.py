"""utaten HTTP 클라이언트 — 호출 간격·재시도·User-Agent·디스크 캐시 (SPEC-002 §3.3, NF2006)."""

from __future__ import annotations

import hashlib
import logging
import time
from pathlib import Path

import requests

BASE_URL = "https://utaten.com"
RETRY_STATUS = {429, 500, 502, 503, 504}
log = logging.getLogger(__name__)


class FetchError(RuntimeError):
    pass


class UtatenClient:
    def __init__(
        self,
        interval_sec: float = 3.0,
        max_retries: int = 3,
        contact: str | None = None,
        cache_dir: str | Path | None = None,
        session=None,
        sleep=time.sleep,
        clock=time.monotonic,
        timeout: float = 20.0,
    ):
        self.interval_sec = interval_sec
        self.max_retries = max_retries
        if not contact:
            log.warning("연락처(WIKI_CONTACT)가 없어 User-Agent에 연락처를 넣지 못했습니다.")
        self.user_agent = f"JPopLyricLens/0.1 (+mailto:{contact or 'unknown'})"
        self.cache_dir = Path(cache_dir) if cache_dir else None
        self.session = session or requests.Session()
        self._sleep, self._clock = sleep, clock
        self.timeout = timeout
        self._last: float | None = None

    def _cache_path(self, url: str) -> Path | None:
        if not self.cache_dir:
            return None
        return self.cache_dir / (hashlib.sha1(url.encode()).hexdigest() + ".html")

    def _wait_turn(self) -> None:
        if self._last is not None:
            remaining = self.interval_sec - (self._clock() - self._last)
            if remaining > 0:
                self._sleep(remaining)
        self._last = self._clock()

    def get(self, path: str) -> str:
        url = path if path.startswith("http") else BASE_URL + path
        cached = self._cache_path(url)
        if cached and cached.exists():
            return cached.read_text(encoding="utf-8")

        for attempt in range(self.max_retries + 1):
            self._wait_turn()
            try:
                resp = self.session.get(
                    url, headers={"User-Agent": self.user_agent}, timeout=self.timeout
                )
            except requests.RequestException as exc:
                error = f"연결 오류: {exc}"
            else:
                if resp.status_code == 200:
                    if cached:
                        cached.parent.mkdir(parents=True, exist_ok=True)
                        cached.write_text(resp.text, encoding="utf-8")
                    return resp.text
                if resp.status_code not in RETRY_STATUS:
                    raise FetchError(f"{resp.status_code} {url}")
                error = f"{resp.status_code} {url}"
            if attempt < self.max_retries:
                self._sleep(2**attempt * self.interval_sec)
        raise FetchError(error)
