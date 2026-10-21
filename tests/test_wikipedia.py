import json

from lyriclens.collect.wikipedia import BundleWikiClient, WikiClient
from tests.fakes import FakeClock, FakeResponse, FakeSession

SEARCH = json.dumps({"query": {"search": [
    {"pageid": 7, "title": "레몬 (노래)",
     "snippet": "<span class=\"searchmatch\">요네즈</span> 켄시의 곡"}
]}})
PAGE = json.dumps({"query": {"pages": [
    {"pageid": 7, "title": "레몬 (노래)", "fullurl": "https://ko.wikipedia.org/wiki/x",
     "extract": "본문"}
]}})


def _client(session, clock):
    return WikiClient(contact="me@example.com", interval_sec=1.0, max_retries=3,
                      session=session, sleep=clock.sleep, clock=clock.monotonic)


def test_search_and_fetch():
    """T-F2004-4 검색 후보와 본문·URL을 읽는다."""
    session = FakeSession([FakeResponse(200, SEARCH), FakeResponse(200, PAGE)])
    c = _client(session, FakeClock())
    cands = c.search("레몬", 5)
    assert cands[0].page_id == 7 and cands[0].snippet == "요네즈 켄시의 곡"
    page = c.fetch(7)
    assert (page.title, page.text) == ("레몬 (노래)", "본문")
    assert page.url == "https://ko.wikipedia.org/wiki/x"
    assert session.calls[0]["params"]["srsearch"] == "레몬"


def test_etiquette():
    """T-F2004-5 UA 연락처, 1초 간격, 429 재시도."""
    clock = FakeClock()
    session = FakeSession([FakeResponse(429), FakeResponse(200, SEARCH), FakeResponse(200, SEARCH)])
    c = _client(session, clock)
    c.search("a", 5)
    t = clock.now
    c.search("b", 5)
    assert clock.now - t >= 1.0
    assert len(session.calls) == 3
    assert all("me@example.com" in x["headers"]["User-Agent"] for x in session.calls)


def test_find_page_missing():
    """T-F2004-4 없는 문서는 None."""
    body = json.dumps({"query": {"pages": [{"title": "없음", "missing": True}]}})
    c = _client(FakeSession([FakeResponse(200, body)]), FakeClock())
    assert c.find_page("없음") is None


def test_bundle_client(tmp_path):
    """T-F2004-7 묶음 파일로 같은 인터페이스를 제공한다."""
    (tmp_path / "a.json").write_text(json.dumps(
        {"page_id": 3, "title": "요네즈 켄시", "url": "u", "text": "일본의 싱어송라이터"}
    ), encoding="utf-8")
    c = BundleWikiClient(tmp_path)
    assert [x.page_id for x in c.search("싱어송라이터", 5)] == [3]
    assert c.find_page("요네즈 켄시").page_id == 3
    assert c.fetch(3).text == "일본의 싱어송라이터"
