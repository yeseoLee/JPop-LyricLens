import pytest

from lyriclens.domain.utaten_client import FetchError, UtatenClient
from tests.fakes import FakeClock, FakeResponse, FakeSession


def _client(session, clock, **kw):
    return UtatenClient(
        interval_sec=3.0, max_retries=3, contact="me@example.com",
        session=session, sleep=clock.sleep, clock=clock.monotonic, **kw,
    )


def test_interval_and_user_agent():
    """T-NF2006-1 연속 요청 사이 간격을 지키고 UA에 연락처를 넣는다."""
    clock, session = FakeClock(), FakeSession()
    c = _client(session, clock)
    c.get("/a")
    t1 = clock.now
    c.get("/b")
    assert clock.now - t1 >= 3.0
    assert all("me@example.com" in call["headers"]["User-Agent"] for call in session.calls)
    assert session.calls[0]["url"] == "https://utaten.com/a"


def test_retry_on_429_and_no_retry_on_404():
    """T-NF2006-2 429는 재시도하고 404는 바로 실패한다."""
    clock = FakeClock()
    session = FakeSession([FakeResponse(429), FakeResponse(200, "ok")])
    assert _client(session, clock).get("/x") == "ok"
    assert len(session.calls) == 2

    session = FakeSession([FakeResponse(404)])
    with pytest.raises(FetchError):
        _client(session, FakeClock()).get("/y")
    assert len(session.calls) == 1


def test_gives_up_after_max_retries():
    """T-NF2006-2 재시도 한도를 넘으면 FetchError."""
    session = FakeSession([FakeResponse(503)] * 5)
    with pytest.raises(FetchError):
        _client(session, FakeClock()).get("/z")
    assert len(session.calls) == 4  # 최초 1회 + 재시도 3회


def test_disk_cache(tmp_path):
    """T-NF2006-3 캐시 디렉터리가 있으면 같은 URL은 한 번만 요청한다."""
    session = FakeSession(default="<html>cached</html>")
    c = _client(session, FakeClock(), cache_dir=tmp_path)
    assert c.get("/same") == c.get("/same") == "<html>cached</html>"
    assert len(session.calls) == 1
