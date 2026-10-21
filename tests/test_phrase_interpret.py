import json

from lyriclens.config import load_settings
from lyriclens.domain.indexing import index_songs
from lyriclens.index.store import IndexDoc, VectorStore
from lyriclens.services.phrase_interpret import interpret_phrase
from tests.fakes import FakeChatModel, FakeEmbeddings, make_song

LONG = "一行目\n二行目\n三行目\n四行目\n五行目\n六行目"


def _store(tmp_path, lyrics=None):
    store = VectorStore(tmp_path, FakeEmbeddings())
    song = make_song("ut_aa0001", **({"lyrics": lyrics} if lyrics else {}))
    index_songs([song], store, item_text_max_chars=6000, lyrics_chunk_lines=8)
    store.upsert(
        "wiki_docs",
        [
            IndexDoc(
                "ut_aa0001:5:0",
                "TVアニメ「テスト」은 별을 다룬 작품",
                {
                    "song_id": "ut_aa0001",
                    "doc_title": "테스트 (애니메이션)",
                    "doc_id": 5,
                    "url": "w",
                    "source_type": "wikipedia",
                },
            )
        ],
    )
    return store


def _resp(**kw):
    data = {
        "translation": "별의 거리에서 기다리고 있어",
        "notes": ["待ってる: 기다리고 있다"],
        "background": "타이업 애니메이션과 연결된다 [근거 1]",
    }
    data.update(kw)
    return json.dumps(data, ensure_ascii=False)


def test_interpret_ok(tmp_path):
    """T-F2010-1 해석 결과 구조와 인용 근거."""
    chat = FakeChatModel([_resp()])
    res = interpret_phrase(
        "ut_aa0001", "星の街で  待ってる", "ko", _store(tmp_path), chat, load_settings()
    )
    assert res.status == "ok"
    assert (
        res.translation
        and res.notes == ["待ってる: 기다리고 있다"]
        and "[근거 1]" in res.background
    )
    assert [e.num for e in res.citations] == [1]
    human = chat.calls[0][-1].content
    assert "(가사)" in human and "(곡 정보)" in human and "星の街で待ってる" in human


def test_phrase_not_in_lyrics(tmp_path):
    """T-F2010-2 가사에 없는 구절이면 LLM을 부르지 않는다."""
    chat = FakeChatModel([_resp()])
    res = interpret_phrase(
        "ut_aa0001", "存在しない歌詞", "ko", _store(tmp_path), chat, load_settings()
    )
    assert res.status == "not_found" and chat.calls == []


def test_original_quote_limited(tmp_path):
    """T-F2010-3 원문 인용은 설정 줄 수를 넘지 않는다."""
    res = interpret_phrase(
        "ut_aa0001",
        LONG,
        "en",
        _store(tmp_path, lyrics=LONG),
        FakeChatModel([_resp()]),
        load_settings(),
    )
    assert len(res.original.splitlines()) <= load_settings().display["lyrics_quote_max_lines"] + 1
    assert res.original.endswith("…")


def test_interpret_prompt_rules(tmp_path):
    """T-F2010-8 해석 프롬프트에 근거 사용·대상 언어·JSON 규칙이 있다."""
    chat = FakeChatModel([_resp()])
    interpret_phrase("ut_aa0001", "星の街で待ってる", "en", _store(tmp_path), chat, load_settings())
    system = chat.calls[0][0].content
    assert "근거" in system and "JSON" in system and "English" in system
