from lyriclens.collect.cache import CollectCache
from lyriclens.collect.collector import collect_documents
from lyriclens.collect.models import SongInfo
from lyriclens.config import load_settings
from tests.fakes import FakeChatModel, FakeWikiClient

SONG = SongInfo("ut_1", "Lemon", "米津玄師", "요네즈 켄시")
LONG = "가" * 300
PAGES = [
    {"page_id": 1, "title": "Lemon", "url": "u1", "text": "짧음"},
    {"page_id": 2, "title": "요네즈 켄시", "url": "u2", "text": LONG},
    {"page_id": 3, "title": "언내추럴", "url": "u3", "text": LONG},
    {"page_id": 4, "title": "레몬 (과일)", "url": "u4", "text": LONG},
]
SEARCH = {"드라마 언내추럴": [3, 4], "Lemon": [1, 4], "요네즈 켄시": [2]}


def _run(tmp_path, chat=None, wiki=None, cache=None):
    chat = chat or FakeChatModel(['["드라마 언내추럴"]', "[3]"])
    wiki = wiki or FakeWikiClient(PAGES, SEARCH)
    cache = cache or CollectCache(tmp_path / "c.json")
    return collect_documents(SONG, "주제가?", chat, wiki, cache, load_settings()), wiki, cache


def test_only_selected_fetched(tmp_path):
    """T-F2004-1 선별된 2차 문서만 본문을 받는다."""
    result, wiki, _ = _run(tmp_path)
    fetched = [p for k, p in wiki.calls if k == "fetch"]
    assert 4 not in fetched and 3 in fetched


def test_primary_always_collected(tmp_path):
    """T-F2004-2 곡 문서는 선별에서 빠지고 짧아도 수집된다."""
    result, _, _ = _run(tmp_path)
    primary = {d.page.page_id for d in result.indexed if d.is_primary}
    assert primary == {1, 2}


def test_cache_prevents_recollect(tmp_path):
    """T-F2004-3 같은 곡·질문 두 번째 수집에서는 위키 search/fetch가 0회."""
    _, _, cache = _run(tmp_path)
    result, wiki, _ = _run(tmp_path, cache=CollectCache(tmp_path / "c.json"))
    assert wiki.count("search") == 0 and wiki.count("fetch") == 0
    assert result.indexed == [] and set(result.cached_queries) >= {"드라마 언내추럴"}


def test_result_fields_and_discarded(tmp_path):
    """T-F2004-4, T-F2004-6 문서 필드와 버린 후보가 결과에 있다."""
    result, _, _ = _run(tmp_path)
    for d in result.indexed:
        assert d.page.title and d.page.url and d.page.page_id and d.page.text and d.query
    assert [c.page_id for c in result.discarded] == [4]
    assert result.queries[:2] == ["Lemon", "요네즈 켄시"]
