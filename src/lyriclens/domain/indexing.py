"""곡 목록을 song_meta / song_lyrics 컬렉션에 색인 (F2002)."""

from __future__ import annotations

from lyriclens.domain.documents import song_lyric_docs, song_meta_doc
from lyriclens.domain.models import Song

SONG_META = "song_meta"
SONG_LYRICS = "song_lyrics"


def index_songs(songs: list[Song], store, item_text_max_chars: int, lyrics_chunk_lines: int):
    meta_docs = [song_meta_doc(s, item_text_max_chars) for s in songs]
    lyric_docs = [d for s in songs for d in song_lyric_docs(s, lyrics_chunk_lines)]
    store.upsert(SONG_META, meta_docs)
    store.upsert(SONG_LYRICS, lyric_docs)
    counts = {SONG_META: store.count(SONG_META), SONG_LYRICS: store.count(SONG_LYRICS)}
    print(f"색인 완료: song_meta {counts[SONG_META]}건 / song_lyrics {counts[SONG_LYRICS]}건")
    return counts
