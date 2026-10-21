"""프롬프트 1 — 외부 문서 검색어 추출 (F2003)."""

from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage

from lyriclens.collect.models import SongInfo
from lyriclens.jsonparse import invoke_json
from lyriclens.rag import prompts


def _dedupe(items: list[str]) -> list[str]:
    out: list[str] = []
    for item in items:
        item = " ".join(str(item).split())
        if item and item not in out:
            out.append(item)
    return out


def extract_queries(song: SongInfo, question: str, chat, max_queries: int) -> list[str]:
    base = _dedupe([song.title, song.artist_query])
    messages = [
        SystemMessage(prompts.QUERY_EXTRACTION_SYSTEM.format(max_queries=max_queries)),
        HumanMessage(prompts.QUERY_EXTRACTION_HUMAN.format(
            title=song.title, artist=song.artist_query, tieup=song.tieup or "없음",
            question=question,
        )),
    ]
    extra = invoke_json(chat, messages, list) or []
    extra = [q for q in _dedupe([q for q in extra if isinstance(q, str)]) if q not in base]
    return base + extra[:max_queries]
