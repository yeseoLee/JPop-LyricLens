"""곡·아티스트 문서(1차 문서) 미리 수집 (SPEC-014 §2-2)."""

from __future__ import annotations

from datetime import datetime, timezone

from lyriclens.collect.cache import CollectCache
from lyriclens.collect.collector import primary_docs
from lyriclens.collect.models import CollectedDoc, SongInfo
from lyriclens.index.chunking import WIKI_DOCS, wiki_chunk_docs


def prefetch_primary(songs: list[SongInfo], wiki, cache: CollectCache, store, settings,
                     on_song=lambda song, n: None) -> int:
    """아직 1차 문서를 수집하지 않은 곡만 처리하고, 처리한 곡 수를 돌려준다."""
    done = 0
    for song in songs:
        if cache.primary_done(song.song_id):
            continue
        known = cache.page_ids(song.song_id)
        docs = [
            CollectedDoc(page or wiki.fetch(cand.page_id), query, True)
            for cand, query, page in primary_docs(song, wiki, settings.collect)
            if cand.page_id not in known
        ]
        chunks = wiki_chunk_docs(
            song, docs, settings.chunking["chunk_size"], settings.chunking["chunk_overlap"],
            datetime.now(timezone.utc).isoformat(timespec="seconds"),
        )
        if chunks:
            store.upsert(WIKI_DOCS, chunks)
        cache.add(song.song_id, [], [d.page.page_id for d in docs])
        cache.mark_primary_done(song.song_id)
        on_song(song, len(chunks))
        done += 1
    return done
