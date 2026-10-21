"""테스트 대역 모음. 외부 호출(utaten, 위키백과, LLM, 임베딩)은 여기의 가짜 객체로 바꾼다."""

from __future__ import annotations

from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures"


def fixture_text(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


class FakeResponse:
    def __init__(self, status_code: int = 200, text: str = ""):
        self.status_code = status_code
        self.text = text


class FakeSession:
    """requests.Session 대역. 준비된 응답을 차례로 돌려주고 호출을 기록한다."""

    def __init__(self, responses: list[FakeResponse] | None = None, default: str = "<html></html>"):
        self.responses = list(responses or [])
        self.default = default
        self.calls: list[dict] = []

    def get(self, url, headers=None, timeout=None, params=None):
        self.calls.append({"url": url, "headers": headers or {}, "params": params})
        if self.responses:
            resp = self.responses.pop(0)
            if isinstance(resp, Exception):
                raise resp
            return resp
        return FakeResponse(200, self.default)


class FakeClock:
    """time.monotonic / time.sleep 대역. sleep 하면 시간이 흐른다."""

    def __init__(self):
        self.now = 0.0
        self.sleeps: list[float] = []

    def monotonic(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


class FakeUtatenClient:
    """경로 → HTML 사전으로 동작하는 UtatenClient 대역."""

    def __init__(self, pages: dict[str, str]):
        self.pages = pages
        self.calls: list[str] = []

    def get(self, path: str) -> str:
        self.calls.append(path)
        from lyriclens.domain.utaten_client import FetchError

        for key, html in self.pages.items():
            if path.startswith(key):
                return html
        raise FetchError(f"404 {path}")
