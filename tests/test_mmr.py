import math

from lyriclens.config import load_settings
from lyriclens.index.store import IndexDoc, VectorStore
from lyriclens.rag.retrieve import retrieve

# 문장 → 벡터를 직접 정한다: dup1~3 은 거의 같고 질의와 가장 가깝다, other1·2 는 다른 방향
VECS = {
    "q": [1.0, 0.0, 0.0],
    "dup1": [0.95, 0.31, 0.0],
    "dup2": [0.95, 0.30, 0.01],
    "dup3": [0.94, 0.32, 0.0],
    "other1": [0.70, 0.0, 0.71],
    "other2": [0.60, -0.5, 0.62],
}


class VecEmb:
    def _v(self, t):
        v = VECS.get(t, [0.0, 0.0, 1.0])
        n = math.sqrt(sum(x * x for x in v))
        return [x / n for x in v]

    def embed_documents(self, texts):
        return [self._v(t) for t in texts]

    def embed_query(self, t):
        return self._v(t)


def _store(tmp_path):
    store = VectorStore(tmp_path, VecEmb())
    docs = [
        IndexDoc(
            f"s:1:{i}",
            t,
            {"song_id": "s", "doc_id": i, "doc_title": t, "url": "u", "source_type": "wikipedia"},
        )
        for i, t in enumerate(["dup1", "dup2", "dup3", "other1", "other2"])
    ]
    store.upsert("wiki_docs", docs)
    store.upsert(
        "song_meta",
        [
            IndexDoc(
                "s",
                "meta",
                {
                    "song_id": "s",
                    "title": "T",
                    "artist": "A",
                    "url": "u",
                    "source_type": "song_meta",
                },
            )
        ],
    )
    return store


def test_mmr_diversifies(tmp_path):
    """T-F2014-1 유사도 검색은 거의 같은 청크를 몰아 고르고 MMR 은 다른 청크를 넣는다."""
    store = _store(tmp_path)
    sim = [d.text for d, _ in store.search("wiki_docs", "q", 3)]
    mmr = [d.text for d, _ in store.search_mmr("wiki_docs", "q", 3, fetch_k=5, lambda_mult=0.5)]
    assert set(sim) == {"dup1", "dup2", "dup3"}
    assert mmr[0] in {"dup1", "dup2", "dup3"} and any(t.startswith("other") for t in mmr)


def test_lambda_one_equals_similarity(tmp_path):
    """T-F2014-2 lambda=1 이면 유사도 검색과 같은 순서."""
    store = _store(tmp_path)
    sim = [d.id for d, _ in store.search("wiki_docs", "q", 4)]
    mmr = [d.id for d, _ in store.search_mmr("wiki_docs", "q", 4, fetch_k=5, lambda_mult=1.0)]
    assert sim == mmr


def test_retrieve_with_mmr(tmp_path):
    """T-F2014-3 search_type=mmr 여도 곡 정보 1번 고정·위키 근거 수 유지."""
    settings = load_settings(
        overrides={
            "retrieval": {
                **load_settings().retrieval,
                "search_type": "mmr",
                "wiki_top_k": 3,
                "mmr_fetch_k": 5,
            }
        }
    )
    ev = retrieve(_store(tmp_path), "s", "q", settings)
    assert ev[0].source_type == "song_meta"
    wiki = [e.text for e in ev if e.source_type == "wikipedia"]
    assert len(wiki) == 3 and any(t.startswith("other") for t in wiki)


def test_diversity_summary():
    """T-F2014-4 비교 도구 요약: 서로 다른 문서 수와 평균 유사도."""
    from lyriclens.bench.diversity import diversity_summary
    from lyriclens.rag.evidence import Evidence

    ev = [
        Evidence(i + 1, f"c{i}", "wikipedia", "t", "u", t, {"doc_id": d})
        for i, (t, d) in enumerate([("dup1", 1), ("dup2", 1), ("other1", 2)])
    ]
    out = diversity_summary(ev, VecEmb())
    assert out["distinct_docs"] == 2
    assert 0 < out["mean_pairwise_sim"] < 1
