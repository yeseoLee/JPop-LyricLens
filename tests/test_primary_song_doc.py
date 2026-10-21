from lyriclens.collect.cache import CollectCache
from lyriclens.collect.collector import collect_documents
from lyriclens.collect.models import SongInfo
from lyriclens.config import load_settings
from tests.fakes import FakeChatModel, FakeWikiClient

SONG = SongInfo("ut_y1", "夜に駆ける", "YOASOBI", "요아소비")
LONG = "가" * 300


def _run(pages, search_map, tmp_path, settings=None):
    wiki = FakeWikiClient(pages, search_map)
    result = collect_documents(
        SONG,
        "원작 소설은?",
        FakeChatModel(["[]"]),
        wiki,
        CollectCache(tmp_path / "c.json"),
        settings or load_settings(),
    )
    return result, wiki


def test_translated_title_is_primary(tmp_path):
    """T-F2004-9 번역 제목 곡 문서도 본문 확인 후 1차 문서로 수집한다."""
    pages = [
        {"page_id": 10, "title": "밤 (동음이의어)", "url": "u10", "text": "밤은 해가 진 뒤의 시간"},
        {
            "page_id": 11,
            "title": "밤을 달리다",
            "url": "u11",
            "text": "「밤을 달리다」(夜に駆ける)는 요아소비의 데뷔곡이다. " + LONG,
        },
        {"page_id": 12, "title": "요아소비", "url": "u12", "text": "일본의 2인조 " + LONG},
    ]
    result, wiki = _run(pages, {"夜に駆ける": [10, 11]}, tmp_path)
    primary = {d.page.page_id for d in result.indexed if d.is_primary}
    assert primary == {11, 12}
    assert [p for k, p in wiki.calls if k == "fetch"].count(11) == 1


def test_homonym_redirect_rejected(tmp_path):
    """T-F2004-10 아티스트 언급이 없는 동음이의어 문서는 곡 문서가 아니다."""
    song = SongInfo("ut_l1", "Lemon", "米津玄師", "요네즈 켄시")
    pages = [
        {
            "page_id": 20,
            "title": "레몬",
            "url": "u20",
            "text": "Lemon은 운향과의 과일이다. " + LONG,
        },
        {"page_id": 21, "title": "요네즈 켄시", "url": "u21", "text": "일본의 가수 " + LONG},
    ]
    wiki = FakeWikiClient(pages, {})
    wiki.find_page = lambda title: (
        wiki.calls.append(("find_page", title))
        or (
            wiki._cand(20, "레몬", "")
            if title == "Lemon"
            else FakeWikiClient.find_page(wiki, title)
        )
    )
    result = collect_documents(
        song, "q", FakeChatModel(["[]"]), wiki, CollectCache(tmp_path / "c.json"), load_settings()
    )
    primary = {d.page.page_id for d in result.indexed if d.is_primary}
    assert primary == {21}


def test_verify_limit(tmp_path):
    """T-F2004-11 본문 확인은 primary_verify_limit 개까지만."""
    pages = [{"page_id": i, "title": f"무관{i}", "url": f"u{i}", "text": LONG} for i in range(1, 8)]
    settings = load_settings(overrides={"collect": {"primary_verify_limit": 2}})
    _, wiki = _run(
        pages, {"夜に駆ける": [1, 2, 3, 4], "夜に駆ける 요아소비": [5, 6]}, tmp_path, settings
    )
    assert len([p for k, p in wiki.calls if k == "fetch"]) <= 2


def test_disambiguation_skipped_and_paren_rule(tmp_path):
    """T-F2004-12 동음이의어는 빼고 '곡 (아티스트의 노래)' 문서를 본문 확인 없이 고른다."""
    song = SongInfo("ut_i1", "アイドル", "YOASOBI", "요아소비")
    pages = [
        {
            "page_id": 30,
            "title": "아이돌 (동음이의)",
            "url": "u30",
            "text": "アイドル는 요아소비의 곡 등을 가리킨다. " + LONG,
        },
        {"page_id": 31, "title": "아이돌 (요아소비의 노래)", "url": "u31", "text": LONG},
        {"page_id": 32, "title": "요아소비", "url": "u32", "text": LONG},
    ]
    wiki = FakeWikiClient(pages, {"アイドル": [30], "アイドル 요아소비": [31]})
    result = collect_documents(
        song, "q", FakeChatModel(["[]"]), wiki, CollectCache(tmp_path / "c.json"), load_settings()
    )
    primary = {d.page.page_id for d in result.indexed if d.is_primary}
    assert primary == {31, 32}
    assert 30 not in [p for k, p in wiki.calls if k == "fetch"]
