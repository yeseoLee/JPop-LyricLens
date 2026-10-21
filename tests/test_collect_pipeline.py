from lyriclens.collect.cache import CollectCache
from lyriclens.collect.models import SongInfo
from lyriclens.collect.pipeline import collect_and_index
from lyriclens.config import load_settings
from lyriclens.index.store import VectorStore
from tests.fakes import FakeChatModel, FakeEmbeddings, FakeWikiClient

PAGES = [
    {"page_id": 1, "title": "Lemon", "url": "u1", "text": "요네즈 켄시의 곡. " * 200},
    {"page_id": 2, "title": "요네즈 켄시", "url": "u2", "text": "싱어송라이터. " * 50},
]


def test_collect_and_index(tmp_path):
    """T-F2005-5 수집 문서를 wiki_docs 에 색인하고 청크 수를 돌려준다."""
    store = VectorStore(tmp_path / "chroma", FakeEmbeddings())
    result = collect_and_index(
        SongInfo("ut_1", "Lemon", "米津玄師", "요네즈 켄시"), "q",
        FakeChatModel(["[]"]), FakeWikiClient(PAGES), CollectCache(tmp_path / "c.json"),
        store, load_settings(),
    )
    assert result.chunk_count == store.count("wiki_docs") > 2
    assert {d.page.page_id for d in result.indexed} == {1, 2}
