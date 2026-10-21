"""곡 → 색인 문서 변환 (docs/SPEC.md §3.2). 컬렉션 메타데이터 규칙은 여기서만 정한다."""

from __future__ import annotations

from lyriclens.domain.item_text import build_item_text
from lyriclens.domain.lyrics import split_stanzas
from lyriclens.domain.models import Song
from lyriclens.index.store import IndexDoc


def _clean(metadata: dict) -> dict:
    return {k: v for k, v in metadata.items() if v is not None}


def song_meta_doc(song: Song, max_chars: int) -> IndexDoc:
    metadata = {
        "song_id": song.song_id,
        "title": song.title,
        "title_kana": song.title_kana,
        "artist": song.artist,
        "artist_ko": song.artist_ko,
        "lyricist": song.lyricist,
        "composer": song.composer,
        "release_date": song.release_date,
        "release_year": song.release_year,
        "tieup": song.tieup,
        "url": song.url,
        "source_type": "song_meta",
    }
    return IndexDoc(song.song_id, build_item_text(song, max_chars), _clean(metadata))


def song_lyric_docs(song: Song, max_lines: int) -> list[IndexDoc]:
    return [
        IndexDoc(
            f"{song.song_id}:L{seq}",
            stanza,
            _clean({
                "song_id": song.song_id,
                "title": song.title,
                "artist": song.artist,
                "stanza_seq": seq,
                "url": song.url,
                "source_type": "lyrics",
            }),
        )
        for seq, stanza in enumerate(split_stanzas(song.lyrics, max_lines))
    ]
