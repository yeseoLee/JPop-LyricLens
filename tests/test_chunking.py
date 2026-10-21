from lyriclens.collect.models import CollectedDoc, SongInfo, WikiPage
from lyriclens.index.chunking import chunk_id, split_text, wiki_chunk_docs
from lyriclens.index.store import VectorStore
from tests.fakes import FakeEmbeddings

TEXT = "\n\n".join(f"{i}번째 문단입니다. " + "가나다라마바사 " * 30 for i in range(6))
PAGE = WikiPage(77, "언내추럴", "https://ko.wikipedia.org/wiki/언내추럴", TEXT)


def _docs(song_id, size=1000, overlap=200):
    song = SongInfo(song_id, "Lemon", "米津玄師", "요네즈 켄시")
    return wiki_chunk_docs(song, [CollectedDoc(PAGE, "언내추럴", False)], size, overlap,
                           "2026-10-21T00:00:00")


def test_chunk_ids():
    """T-F2005-1 청크 ID는 {song_id}:{page_id}:{seq}."""
    docs = _docs("ut_1")
    assert chunk_id("ut_1", 77, 0) == "ut_1:77:0"
    assert [d.id for d in docs] == [f"ut_1:77:{i}" for i in range(len(docs))]


def test_same_doc_two_songs_no_overwrite(tmp_path):
    """T-F2005-2 두 곡이 같은 문서를 색인해도 덮어쓰지 않는다."""
    store = VectorStore(tmp_path, FakeEmbeddings())
    a, b = _docs("ut_1"), _docs("ut_2")
    store.upsert("wiki_docs", a)
    store.upsert("wiki_docs", b)
    assert store.count("wiki_docs") == len(a) + len(b)


def test_chunk_size_changes_count():
    """T-F2005-3 chunk_size를 줄이면 청크 수가 늘어난다."""
    assert len(split_text(TEXT, 300, 50)) > len(split_text(TEXT, 1000, 200))
    assert len(_docs("ut_1", 300, 50)) > len(_docs("ut_1", 1000, 200))


def test_chunk_metadata():
    """T-F2005-4 청크 메타데이터에 필수 필드가 있다."""
    md = _docs("ut_1")[0].metadata
    assert md["doc_title"] == "언내추럴" and md["url"].startswith("https://")
    assert md["song_id"] == "ut_1" and md["doc_id"] == 77
    assert md["source_type"] == "wikipedia" and md["is_primary"] is False
    assert md["query"] == "언내추럴" and md["song_title"] == "Lemon"


def test_empty_text_no_chunks():
    """T-F2005-4 본문이 빈 문서는 청크가 없다."""
    song = SongInfo("ut_1", "Lemon", "米津玄師")
    empty = CollectedDoc(WikiPage(1, "빈", "u", "  "), "q", True)
    assert wiki_chunk_docs(song, [empty], 1000, 200, "t") == []
