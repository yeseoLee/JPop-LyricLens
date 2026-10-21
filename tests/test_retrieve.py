from lyriclens.config import load_settings
from lyriclens.index.store import IndexDoc, VectorStore
from lyriclens.rag.retrieve import retrieve
from tests.fakes import FakeEmbeddings

Q = "언내추럴 드라마 주제가"


def _store(tmp_path, wiki_n=8):
    store = VectorStore(tmp_path, FakeEmbeddings())
    store.upsert(
        "song_meta",
        [
            IndexDoc(
                "ut_a",
                "제목: Lemon",
                {
                    "song_id": "ut_a",
                    "title": "Lemon",
                    "artist": "米津玄師",
                    "url": "https://utaten.com/lyric/a/",
                    "source_type": "song_meta",
                },
            ),
            IndexDoc(
                "ut_b",
                Q,
                {
                    "song_id": "ut_b",
                    "title": "B",
                    "artist": "x",
                    "url": "ub",
                    "source_type": "song_meta",
                },
            ),
        ],
    )
    store.upsert(
        "song_lyrics",
        [
            IndexDoc(
                "ut_a:L0",
                "夜の窓に灯がともる",
                {
                    "song_id": "ut_a",
                    "title": "Lemon",
                    "stanza_seq": 0,
                    "url": "https://utaten.com/lyric/a/",
                    "source_type": "lyrics",
                },
            ),
            IndexDoc(
                "ut_b:L0",
                Q,
                {
                    "song_id": "ut_b",
                    "title": "B",
                    "stanza_seq": 0,
                    "url": "ub",
                    "source_type": "lyrics",
                },
            ),
        ],
    )
    wiki = [
        IndexDoc(
            f"ut_a:7:{i}",
            f"언내추럴 문단 {i} 내용",
            {
                "song_id": "ut_a",
                "doc_title": "언내추럴",
                "doc_id": 7,
                "url": "https://ko.wikipedia.org/w",
                "source_type": "wikipedia",
            },
        )
        for i in range(wiki_n)
    ]
    wiki.append(
        IndexDoc(
            "ut_a:9:0",
            "언내추럴 문단 0 내용",
            {  # ut_a:7:0 과 같은 본문, 다른 문서
                "song_id": "ut_a",
                "doc_title": "다른 문서",
                "doc_id": 9,
                "url": "w9",
                "source_type": "wikipedia",
            },
        )
    )
    wiki.append(
        IndexDoc(
            "ut_b:7:0",
            Q,
            {
                "song_id": "ut_b",
                "doc_title": "언내추럴",
                "doc_id": 7,
                "url": "w",
                "source_type": "wikipedia",
            },
        )
    )
    store.upsert("wiki_docs", wiki)
    return store


def _settings(wiki_top_k=3):
    return load_settings(overrides={"retrieval": {"wiki_top_k": wiki_top_k, "lyrics_top_k": 3}})


def test_meta_always_first(tmp_path):
    """T-F2006-1 선택 곡의 곡 정보가 항상 1번 근거다."""
    ev = retrieve(_store(tmp_path), "ut_a", "전혀 상관없는 질문", _settings())
    assert ev[0].chunk_id == "ut_a" and ev[0].source_type == "song_meta"


def test_other_song_excluded(tmp_path):
    """T-F2006-2 다른 곡의 청크는 더 비슷해도 들어가지 않는다."""
    ev = retrieve(_store(tmp_path), "ut_a", Q, _settings())
    assert all(e.metadata["song_id"] == "ut_a" for e in ev)


def test_duplicate_text_removed(tmp_path):
    """T-F2006-3 같은 출처 유형·같은 본문은 하나만 남는다."""
    ev = retrieve(_store(tmp_path, wiki_n=1), "ut_a", "언내추럴 문단 0 내용", _settings(6))
    texts = [e.text for e in ev if e.source_type == "wikipedia"]
    assert len(texts) == len(set(texts))


def test_top_k_from_settings(tmp_path):
    """T-F2006-4 wiki_top_k 설정이 위키 근거 수를 정한다."""
    store = _store(tmp_path)
    n3 = sum(e.source_type == "wikipedia" for e in retrieve(store, "ut_a", Q, _settings(3)))
    n6 = sum(e.source_type == "wikipedia" for e in retrieve(store, "ut_a", Q, _settings(6)))
    assert (n3, n6) == (3, 6)


def test_numbering_and_fields(tmp_path):
    """T-F2006-5 번호는 1..N 연속이고 출처 유형·제목·URL이 채워진다."""
    ev = retrieve(_store(tmp_path), "ut_a", Q, _settings())
    assert [e.num for e in ev] == list(range(1, len(ev) + 1))
    order = [e.source_type for e in ev]
    assert order == sorted(order, key=["song_meta", "lyrics", "wikipedia"].index)
    assert ev[0].title == "Lemon — 米津玄師"
    lyric = next(e for e in ev if e.source_type == "lyrics")
    assert lyric.title == "Lemon 가사 (1연)" and lyric.url
    assert all(e.title and e.url for e in ev)
