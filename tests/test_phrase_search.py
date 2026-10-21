from lyriclens.config import load_settings
from lyriclens.domain.indexing import index_songs
from lyriclens.index.store import VectorStore
from lyriclens.services.phrase_search import search_phrase
from tests.fakes import FakeChatModel, FakeEmbeddings, make_song


def _store(tmp_path, n=4):
    store = VectorStore(tmp_path, FakeEmbeddings())
    songs = [
        make_song(
            f"ut_s{i:04d}",
            title=f"曲{i}",
            lyrics=f"星の街で待ってる{i}\n夜の窓\n\n星の街で待ってる\n君の名前{i}",
        )
        for i in range(n)
    ]
    index_songs(songs, store, item_text_max_chars=6000, lyrics_chunk_lines=8)
    return store


def test_korean_input_translates(tmp_path):
    """T-F2010-4 한국어 입력은 일본어 변환 질의와 원문 질의로 검색한다."""
    chat = FakeChatModel(['["星の街で待ってる"]'])
    hits = search_phrase("별의 거리에서 기다릴게", _store(tmp_path), chat, load_settings())
    assert len(chat.calls) == 1 and hits
    assert "별의 거리에서 기다릴게" in chat.calls[0][-1].content


def test_one_hit_per_song(tmp_path):
    """T-F2010-5 같은 곡은 한 번만 나온다."""
    hits = search_phrase("星の街で待ってる", _store(tmp_path), FakeChatModel(), load_settings())
    ids = [h.song_id for h in hits]
    assert len(ids) == len(set(ids)) == 4


def test_limit_and_order(tmp_path):
    """T-F2010-6 결과 수 제한, 점수 내림차순, 일치 구절 2줄 이하."""
    settings = load_settings(overrides={"retrieval": {"phrase_search_top_k": 2}})
    hits = search_phrase("星の街で待ってる", _store(tmp_path), FakeChatModel(), settings)
    assert len(hits) == 2
    assert hits[0].score >= hits[1].score
    assert all(len(h.matched.splitlines()) <= 3 for h in hits)  # 2줄 + "…"
    assert hits[0].url and hits[0].title


def test_japanese_no_llm(tmp_path):
    """T-F2010-7 일본어 입력은 LLM을 부르지 않는다."""
    chat = FakeChatModel()
    search_phrase("星の街で待ってる", _store(tmp_path), chat, load_settings())
    assert chat.calls == []
