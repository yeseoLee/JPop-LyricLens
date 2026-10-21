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


def test_backoff_on_connection_error():
    """T-NF2006-2 연결 오류에도 지수 백오프로 재시도하고, 마지막 실패 뒤에는 기다리지 않는다."""
    import requests

    clock = FakeClock()
    session = FakeSession([requests.ConnectionError("x"), requests.ConnectionError("y"),
                           FakeResponse(200, "ok")])
    assert _client(session, clock).get("/c") == "ok"
    assert clock.sleeps[:2] == [3.0, 6.0]  # 2**0*3, 2**1*3 (간격 대기는 이미 충족)

    clock = FakeClock()
    session = FakeSession([requests.ConnectionError("z")] * 4)
    with pytest.raises(FetchError):
        _client(session, clock).get("/d")
    assert sum(clock.sleeps) == 3.0 + 6.0 + 12.0


def test_warns_without_contact(caplog):
    """T-NF2006-1 연락처가 없으면 경고를 남긴다."""
    import logging

    with caplog.at_level(logging.WARNING):
        UtatenClient(contact=None, session=FakeSession())
    assert "연락처" in caplog.text
