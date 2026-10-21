import pytest

from lyriclens.domain.utaten_client import UtatenClient
from lyriclens.domain.utaten_parser import parse_artist_song_ids, parse_song


@pytest.mark.live
def test_live_parse_one_song():
    """T-F2001-1 (live) 실제 utaten 1곡을 파싱한다."""
    c = UtatenClient(contact="live-test@example.com")
    ids = parse_artist_song_ids(c.get("/artist/lyric/8450"))
    song = parse_song(c.get(f"/lyric/{ids[0]}/"), f"https://utaten.com/lyric/{ids[0]}/")
    assert song.title and song.lyrics and song.artist
