"""수집 + 색인을 한 번에 — UI·서비스가 부르는 진입점 (SPEC-005)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from lyriclens.collect.cache import CollectCache
from lyriclens.collect.collector import collect_documents
from lyriclens.collect.models import CollectResult, SongInfo
from lyriclens.index.chunking import WIKI_DOCS, wiki_chunk_docs


@dataclass
class IndexedCollectResult(CollectResult):
    chunk_count: int = 0


def collect_and_index(song: SongInfo, question: str, chat, wiki, cache: CollectCache, store,
                      settings) -> IndexedCollectResult:
    collected = collect_documents(song, question, chat, wiki, cache, settings)
    docs = wiki_chunk_docs(
        song, collected.indexed,
        settings.chunking["chunk_size"], settings.chunking["chunk_overlap"],
        datetime.now(timezone.utc).isoformat(timespec="seconds"),
    )
    if docs:
        store.upsert(WIKI_DOCS, docs)
    return IndexedCollectResult(**vars(collected), chunk_count=len(docs))
