"""조건 기반 곡 탐색 — 조건 해석 → 후보 검색 → LLM 선별 (SPEC-008, F2011)."""

from __future__ import annotations

from dataclasses import dataclass, field

from langchain_core.messages import HumanMessage, SystemMessage

from lyriclens.jsonparse import invoke_json
from lyriclens.rag import prompts

SONG_META = "song_meta"
LYRICS_PREVIEW_LINES = 3


@dataclass
class SongMatch:
    song_id: str
    title: str
    artist: str
    year: int | None
    url: str
    reason: str


@dataclass
class ConditionResult:
    matches: list[SongMatch] = field(default_factory=list)
    status: str = "empty"
    year_filter: dict | None = None


def _year_filter(parsed: dict) -> dict | None:
    clauses = []
    for key, op in (("year_from", "$gte"), ("year_to", "$lte")):
        value = parsed.get(key)
        if isinstance(value, int) and not isinstance(value, bool):
            clauses.append({"release_year": {op: value}})
    if not clauses:
        return None
    return clauses[0] if len(clauses) == 1 else {"$and": clauses}


def _lyrics_head(text: str) -> str:
    _, _, lyrics = text.partition("가사:\n")
    lines = [line for line in lyrics.splitlines() if line.strip()]
    return " / ".join(lines[:LYRICS_PREVIEW_LINES])


def _describe(doc) -> str:
    md = doc.metadata
    return " | ".join([
        doc.id, md.get("title", ""), md.get("artist", ""), str(md.get("release_year", "?")),
        md.get("tieup", "-"), _lyrics_head(doc.text),
    ])


def search_by_condition(condition: str, store, chat, settings) -> ConditionResult:
    parsed = invoke_json(chat, [SystemMessage(prompts.CONDITION_PARSE_SYSTEM),
                                HumanMessage(condition)], dict) or {}
    query = parsed.get("query") if isinstance(parsed.get("query"), str) else None
    where = _year_filter(parsed)
    result = ConditionResult(year_filter=where)

    hits = store.search(SONG_META, query or condition,
                        settings.retrieval["condition_candidates"], where)
    if not hits:
        return result
    candidates = {doc.id: doc for doc, _ in hits}
    human = prompts.CONDITION_SELECT_HUMAN.format(
        condition=condition, candidates="\n".join(_describe(d) for d in candidates.values())
    )
    chosen = invoke_json(chat, [SystemMessage(prompts.CONDITION_SELECT_SYSTEM),
                                HumanMessage(human)], list) or []

    for item in chosen:
        if not isinstance(item, dict) or item.get("song_id") not in candidates:
            continue
        doc = candidates.pop(item["song_id"])
        md = doc.metadata
        result.matches.append(SongMatch(
            doc.id, md.get("title", ""), md.get("artist", ""), md.get("release_year"),
            md.get("url", ""), str(item.get("reason", "")),
        ))
    result.status = "ok" if result.matches else "empty"
    return result
