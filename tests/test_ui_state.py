from lyriclens.ui.state import ChatStore, song_label, song_options, stanza_options


def test_chat_store_separated():
    """T-F2009-1 곡별 대화가 섞이지 않고 history는 최근 4개."""
    store = ChatStore()
    for i in range(3):
        store.add("A", "user", f"a{i}")
        store.add("A", "assistant", f"ra{i}")
    store.add("B", "user", "b0")
    assert [m["content"] for m in store.messages("B")] == ["b0"]
    assert len(store.messages("A")) == 6
    assert store.history("A") == [
        ("user", "a1"),
        ("assistant", "ra1"),
        ("user", "a2"),
        ("assistant", "ra2"),
    ]


def test_song_options():
    """T-F2009-2 라벨 형식과 제목순 정렬."""
    metas = [
        {"song_id": "2", "title": "夜に駆ける", "artist": "YOASOBI", "release_year": 2019},
        {"song_id": "1", "title": "Lemon", "artist": "米津玄師", "release_year": 2018},
        {"song_id": "3", "title": "アイドル", "artist": "YOASOBI"},
    ]
    assert song_label(metas[1]) == "Lemon — 米津玄師 (2018)"
    assert song_label(metas[2]) == "アイドル — YOASOBI"
    assert [sid for _, sid in song_options(metas)] == ["1", "3", "2"]


def test_stanza_options_first_line_only():
    """T-F2012-6 연 선택 목록은 각 연의 첫 줄만 보인다."""
    from lyriclens.index.store import IndexDoc

    docs = [
        IndexDoc("s:L1", "二連目\n続き", {"stanza_seq": 1}),
        IndexDoc("s:L0", "一連目\n続き\nさらに", {"stanza_seq": 0}),
    ]
    assert stanza_options(docs) == [
        ("1. 一連目 …", "一連目\n続き\nさらに"),
        ("2. 二連目 …", "二連目\n続き"),
    ]
