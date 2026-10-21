"""구절로 곡 찾기 — 교차 언어 가사 검색 (SPEC-009 §3.2)."""

from __future__ import annotations

from dataclasses import dataclass

from langchain_core.messages import HumanMessage, SystemMessage

from lyriclens.domain.lyrics import quote_lines
from lyriclens.jsonparse import invoke_json
from lyriclens.rag import prompts
from lyriclens.rag.language import detect_language
from lyriclens.rag.retrieve import SONG_LYRICS

MATCHED_LINES = 2


@dataclass
class PhraseHit:
    song_id: str
    title: str
    artist: str
    url: str
    score: float
    matched: str


def _queries(text: str, chat) -> list[str]:
    queries = [text.strip()]
    if detect_language(text) != "ja":
        translated = invoke_json(chat, [SystemMessage(prompts.PHRASE_TO_JA_SYSTEM),
                                        HumanMessage(text)], list) or []
        queries = [q for q in translated[:2] if isinstance(q, str) and q.strip()] + queries
    return queries


def search_phrase(text: str, store, chat, settings) -> list[PhraseHit]:
    top_k = settings.retrieval["phrase_search_top_k"]
    best: dict[str, PhraseHit] = {}
    for query in _queries(text, chat):
        for doc, score in store.search(SONG_LYRICS, query, top_k * 3):
            song_id = doc.metadata["song_id"]
            if song_id in best and best[song_id].score >= score:
                continue
            md = doc.metadata
            best[song_id] = PhraseHit(song_id, md.get("title", ""), md.get("artist", ""),
                                      md.get("url", ""), score,
                                      quote_lines(doc.text, MATCHED_LINES))
    return sorted(best.values(), key=lambda h: h.score, reverse=True)[:top_k]
