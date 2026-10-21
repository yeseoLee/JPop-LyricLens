import pytest

from lyriclens.domain.utaten_parser import (
    ParseError,
    parse_artist_song_ids,
    parse_search_artists,
    parse_song,
)
from tests.fakes import fixture_text

URL = "https://utaten.com/lyric/zz9999/"


def test_parse_song_fields():
    """T-F2001-1 가사 페이지에서 곡 필드를 모두 읽는다."""
    song = parse_song(fixture_text("utaten_song.html"), URL)
    assert song.song_id == "ut_zz9999"
    assert song.title == "星の街"
    assert song.title_kana == "ほしのまち"
    assert song.artist == "テスト歌手"
    assert song.lyricist == "作詞者A"
    assert song.composer == "作曲者B, 作曲者C"
    assert song.arranger == "編曲者D"
    assert song.release_date == "2021-04-05"
    assert song.url == URL
    assert song.tieup is None
    assert song.lyrics.splitlines()[0] == "夜の窓に灯がともる"
    assert song.lyrics_romaji.startswith("yoru no mado")


def test_ruby_handling():
    """T-F2001-2 원문에는 읽기가 없고, 읽기 가사는 rt로 바뀐다."""
    song = parse_song(fixture_text("utaten_song.html"), URL)
    assert "よる" not in song.lyrics
    assert song.lyrics_kana.splitlines()[0] == "よるのまどにひがともる"
    # 연속 빈 줄은 하나로
    assert song.lyrics.split("\n") == [
        "夜の窓に灯がともる",
        "ねむれない僕の声",
        "",
        "星の街で待ってる",
    ]


def test_parse_song_without_lyrics_raises():
    """T-F2001-8 가사가 없으면 ParseError."""
    with pytest.raises(ParseError):
        parse_song("<html><h2 class='newLyricTitle__main'>x</h2></html>", URL)


def test_artist_song_ids_order_and_dedupe():
    """T-F2001-6 곡 목록은 순서를 유지하고 중복을 없앤다."""
    html = fixture_text("utaten_artist.html")
    assert parse_artist_song_ids(html) == ["aa0001", "bb0002", "cc0003", "dd0004"]


def test_search_artists():
    """T-F2001-7 검색 결과에서 아티스트 이름과 ID를 읽는다."""
    found = parse_search_artists(fixture_text("utaten_search.html"))
    assert ("テスト歌手", "111") in found


def _variant(**replace):
    html = fixture_text("utaten_song.html")
    for old, new in replace.items():
        html = html.replace(old, new)
    return html


def test_unpadded_release_date():
    """T-F2001-9 월·일에 0이 없는 날짜도 정규화한다."""
    song = parse_song(_variant(**{"2021.04.05": "2025.9.4"}), URL)
    assert song.release_date == "2025-09-04"


def test_subtitle_is_tieup():
    """T-F2001-10 부제목은 제목에서 빠지고 tieup 이 된다."""
    sub = '<span class="newLyricTitle__subTitle">TVアニメ「テスト」主題歌</span>'
    html = _variant(**{"</span>\n  </h2>": "</span>" + sub + "\n  </h2>"})
    assert sub in html
    song = parse_song(html, URL)
    assert song.title == "星の街"
    assert song.tieup == "TVアニメ「テスト」主題歌"
