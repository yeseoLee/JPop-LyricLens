import json

from lyriclens.domain.crawl import crawl_artists, write_songs
from tests.fakes import FakeUtatenClient, fixture_text

SONG = fixture_text("utaten_song.html")
ARTIST = fixture_text("utaten_artist.html")


def _pages(**extra):
    pages = {"/search": fixture_text("utaten_search.html"), "/artist/lyric/": ARTIST}
    for lid in ["aa0001", "bb0002", "cc0003", "dd0004"]:
        pages[f"/lyric/{lid}/"] = SONG
    pages.update(extra)
    return pages


def test_crawl_resolves_artist_and_limits_songs():
    """T-F2001-6 아티스트 ID를 찾고 상위 N곡만 수집한다."""
    artists = [{"name": "テスト歌手", "name_ko": "테스트 가수", "utaten_artist_id": None}]
    client = FakeUtatenClient(_pages())
    result = crawl_artists(artists, client, songs_per_artist=2)
    assert [s.song_id for s in result.songs] == ["ut_aa0001", "ut_bb0002"]
    assert result.songs[0].artist_ko == "테스트 가수"
    assert artists[0]["utaten_artist_id"] == "111"


def test_crawl_dedupes_song_ids():
    """T-F2001-5 같은 곡은 한 번만 저장된다."""
    artists = [
        {"name": "A", "name_ko": "에이", "utaten_artist_id": "111"},
        {"name": "B", "name_ko": "비", "utaten_artist_id": "111"},
    ]
    result = crawl_artists(artists, FakeUtatenClient(_pages()), songs_per_artist=3)
    ids = [s.song_id for s in result.songs]
    assert len(ids) == len(set(ids)) == 4  # 목록의 고유 곡 4개뿐


def test_crawl_records_errors_and_skips():
    """T-F2001-8 파싱 실패 곡과 못 찾은 아티스트는 기록하고 계속한다."""
    pages = _pages(**{"/lyric/aa0001/": "<html></html>"})
    artists = [
        {"name": "テスト歌手", "name_ko": "x", "utaten_artist_id": None},
        {"name": "없는가수", "name_ko": "y", "utaten_artist_id": None},
    ]
    client = FakeUtatenClient(pages)
    client.pages["/search"] = fixture_text("utaten_search.html")
    result = crawl_artists(artists, client, songs_per_artist=2)
    # 실패 곡은 건너뛰고 N곡을 채운다
    assert [s.song_id for s in result.songs] == ["ut_bb0002", "ut_cc0003"]
    assert any("aa0001" in e for e in result.errors)
    assert result.skipped == ["없는가수"]


def test_write_songs_reports_and_warns(tmp_path, capsys):
    """T-F2001-4 곡 수를 출력하고 100건 미만이면 경고한다."""
    artists = [{"name": "A", "name_ko": "에이", "utaten_artist_id": "111"}]
    result = crawl_artists(artists, FakeUtatenClient(_pages()), songs_per_artist=2)
    out = tmp_path / "songs.jsonl"
    write_songs(result.songs, out)
    lines = out.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2 and json.loads(lines[0])["song_id"] == "ut_aa0001"
    printed = capsys.readouterr().out
    assert "2곡" in printed and "경고" in printed


def test_duplicates_do_not_reduce_per_artist_count():
    """T-F2001-5 다른 아티스트와 겹친 곡은 건너뛰고 N곡을 채운다."""
    artists = [
        {"name": "A", "name_ko": "에이", "utaten_artist_id": "111"},
        {"name": "B", "name_ko": "비", "utaten_artist_id": "111"},
    ]
    result = crawl_artists(artists, FakeUtatenClient(_pages()), songs_per_artist=2)
    assert [s.song_id for s in result.songs] == [
        "ut_aa0001", "ut_bb0002", "ut_cc0003", "ut_dd0004"
    ]
