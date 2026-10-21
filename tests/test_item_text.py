from lyriclens.domain.documents import song_lyric_docs, song_meta_doc
from lyriclens.domain.item_text import build_item_text
from tests.fakes import make_song


def test_item_text_contains_attributes():
    """T-F2001-3 항목 텍스트에 검색 속성이 모두 들어가고 빈 값 줄은 빠진다."""
    text = build_item_text(make_song(), max_chars=6000)
    for part in ["제목: 星の街 (ほしのまち)", "아티스트: テスト歌手 / 테스트 가수", "작사: 作詞者A",
                 "작곡: 作曲者B", "발매일: 2021-04-05", "타이업: TVアニメ「テスト」主題歌",
                 "가사:", "君の名前を呼んだ"]:
        assert part in text
    assert "편곡" not in text  # arranger None


def test_item_text_truncates_lyrics():
    """T-F2001-3 max_chars를 넘으면 가사 끝을 자른다."""
    song = make_song(lyrics="あ" * 5000)
    text = build_item_text(song, max_chars=300)
    assert len(text) <= 300 and text.startswith("제목:")


def test_meta_doc_metadata():
    """T-F2002-4 메타 문서의 메타데이터에 필수 필드가 있고 None이 없다."""
    doc = song_meta_doc(make_song(arranger=None), max_chars=6000)
    assert doc.id == "ut_aa0001"
    md = doc.metadata
    for key in ["song_id", "title", "artist", "url", "release_year", "source_type"]:
        assert key in md
    assert md["release_year"] == 2021 and md["source_type"] == "song_meta"
    assert None not in md.values()


def test_lyric_docs_ids():
    """T-F2002-4 가사 연 문서 ID는 {song_id}:L{seq}."""
    docs = song_lyric_docs(make_song(), max_lines=8)
    assert [d.id for d in docs] == ["ut_aa0001:L0", "ut_aa0001:L1"]
    assert docs[1].metadata["source_type"] == "lyrics"
    assert docs[1].text.startswith("星の街で待ってる")
