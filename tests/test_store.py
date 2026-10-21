from lyriclens.index.store import IndexDoc, VectorStore
from tests.fakes import FakeEmbeddings


def _docs(n):
    return [IndexDoc(f"id{i}", f"노래 {i} 星の街", {"song_id": f"id{i}"}) for i in range(n)]


def test_upsert_count_idempotent(tmp_path):
    """T-F2002-1, T-F2002-2 N건 색인 시 count=N, 재색인해도 그대로."""
    store = VectorStore(tmp_path, FakeEmbeddings())
    assert store.count("song_meta") == 0
    store.upsert("song_meta", _docs(5))
    store.upsert("song_meta", _docs(5))
    assert store.count("song_meta") == 5


def test_get_and_search(tmp_path):
    """T-F2002-1 ID로 조회하고 필터 검색이 동작한다."""
    store = VectorStore(tmp_path, FakeEmbeddings())
    store.upsert("song_meta", _docs(3))
    got = store.get("song_meta", ["id1"])
    assert got[0].id == "id1" and got[0].metadata["song_id"] == "id1"
    hits = store.search("song_meta", "星の街", k=2, where={"song_id": "id2"})
    assert [d.id for d, _ in hits] == ["id2"]
    assert 0.0 <= hits[0][1] <= 1.0001
