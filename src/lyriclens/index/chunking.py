"""위키 문서 청킹과 청크 ID 규칙 (SPEC-005, F2005)."""

from __future__ import annotations

from langchain_text_splitters import RecursiveCharacterTextSplitter

from lyriclens.collect.models import CollectedDoc, SongInfo
from lyriclens.index.store import IndexDoc

WIKI_DOCS = "wiki_docs"
SEPARATORS = ["\n\n", "\n", "。", ". ", " ", ""]


def split_text(text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size, chunk_overlap=chunk_overlap, separators=SEPARATORS
    )
    return [c for c in splitter.split_text(text) if c.strip()]


def chunk_id(song_id: str, page_id: int, seq: int) -> str:
    return f"{song_id}:{page_id}:{seq}"


def wiki_chunk_docs(song: SongInfo, docs: list[CollectedDoc], chunk_size: int,
                    chunk_overlap: int, collected_at: str) -> list[IndexDoc]:
    out: list[IndexDoc] = []
    for doc in docs:
        page = doc.page
        for seq, text in enumerate(split_text(page.text, chunk_size, chunk_overlap)):
            out.append(IndexDoc(chunk_id(song.song_id, page.page_id, seq), text, {
                "song_id": song.song_id,
                "song_title": song.title,
                "doc_title": page.title,
                "doc_id": page.page_id,
                "url": page.url,
                "query": doc.query,
                "is_primary": doc.is_primary,
                "collected_at": collected_at,
                "source_type": "wikipedia",
            }))
    return out
