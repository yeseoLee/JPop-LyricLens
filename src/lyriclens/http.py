"""외부 API 공통 호출 규칙 — 호출 간격·지수 백오프 재시도·User-Agent (NF2006)."""

from __future__ import annotations

import logging
import time

import requests

RETRY_STATUS = {429, 500, 502, 503, 504}
log = logging.getLogger(__name__)


class FetchError(RuntimeError):
    pass


def user_agent(contact: str | None) -> str:
    if not contact:
        log.warning("연락처(WIKI_CONTACT)가 없어 User-Agent에 연락처를 넣지 못했습니다.")
    return f"JPopLyricLens/0.1 (+mailto:{contact or 'unknown'})"


class PoliteSession:
    def __init__(self, contact, interval_sec, max_retries, session=None,
                 sleep=time.sleep, clock=time.monotonic, timeout=20.0):
        self.user_agent = user_agent(contact)
        self.interval_sec, self.max_retries, self.timeout = interval_sec, max_retries, timeout
        self.session = session or requests.Session()
        self._sleep, self._clock = sleep, clock
        self._last: float | None = None

    def _wait_turn(self) -> None:
        if self._last is not None:
            remaining = self.interval_sec - (self._clock() - self._last)
            if remaining > 0:
                self._sleep(remaining)
        self._last = self._clock()

    def get(self, url: str, params: dict | None = None):
        error = ""
        for attempt in range(self.max_retries + 1):
            self._wait_turn()
            try:
                resp = self.session.get(url, headers={"User-Agent": self.user_agent},
                                        timeout=self.timeout, params=params)
            except requests.RequestException as exc:
                error = f"연결 오류: {exc}"
            else:
                if resp.status_code == 200:
                    return resp
                if resp.status_code not in RETRY_STATUS:
                    raise FetchError(f"{resp.status_code} {url}")
                error = f"{resp.status_code} {url}"
            if attempt < self.max_retries:
                self._sleep(2**attempt * self.interval_sec)
        raise FetchError(error)
