from lyriclens.domain.indexing import index_songs
from lyriclens.index.store import VectorStore
from tests.fakes import FakeEmbeddings, make_song


def test_index_songs_reports(tmp_path, capsys):
    """T-F2002-3 두 컬렉션에 색인하고 건수를 출력한다."""
    store = VectorStore(tmp_path, FakeEmbeddings())
    songs = [make_song("ut_aa0001"), make_song("ut_bb0002")]
    counts = index_songs(songs, store, item_text_max_chars=6000, lyrics_chunk_lines=8)
    assert counts == {"song_meta": 2, "song_lyrics": 4}
    assert store.count("song_meta") == 2 and store.count("song_lyrics") == 4
    out = capsys.readouterr().out
    assert "song_meta 2건" in out and "song_lyrics 4건" in out
