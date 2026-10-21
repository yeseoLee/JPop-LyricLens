"""근거 검색·병합·중복 제거 (SPEC-006, F2006)."""

from __future__ import annotations

from lyriclens.index.store import IndexDoc
from lyriclens.rag.evidence import Evidence

SONG_META, SONG_LYRICS, WIKI_DOCS = "song_meta", "song_lyrics", "wiki_docs"


def evidence_title(doc: IndexDoc, source_type: str) -> str:
    md = doc.metadata
    if source_type == "song_meta":
        return f"{md.get('title', '')} — {md.get('artist', '')}"
    if source_type == "lyrics":
        return f"{md.get('title', '')} 가사 ({int(md.get('stanza_seq', 0)) + 1}연)"
    return md.get("doc_title", "")


def retrieve(store, song_id: str, question: str, settings) -> list[Evidence]:
    cfg = settings.retrieval
    where = {"song_id": song_id}
    rows: list[tuple[IndexDoc, str]] = [(d, "song_meta") for d in store.get(SONG_META, [song_id])]
    rows += [(d, "lyrics") for d, _ in
             store.search(SONG_LYRICS, question, cfg["lyrics_top_k"], where)]
    rows += [(d, "wikipedia") for d, _ in
             store.search(WIKI_DOCS, question, cfg["wiki_top_k"], where)]

    evidence: list[Evidence] = []
    seen_ids: set[str] = set()
    seen_text: set[tuple[str, str]] = set()
    for doc, source_type in rows:
        key = (source_type, doc.text.strip())
        if doc.id in seen_ids or key in seen_text:
            continue
        seen_ids.add(doc.id)
        seen_text.add(key)
        evidence.append(Evidence(
            num=len(evidence) + 1, chunk_id=doc.id, source_type=source_type,
            title=evidence_title(doc, source_type), url=doc.metadata.get("url", ""),
            text=doc.text, metadata=doc.metadata,
        ))
    return evidence
