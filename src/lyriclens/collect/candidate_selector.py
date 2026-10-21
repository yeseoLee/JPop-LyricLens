"""프롬프트 2 — 검색 후보 중 색인할 문서 선별 (F2004)."""

from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage

from lyriclens.collect.models import SongInfo, WikiCandidate
from lyriclens.jsonparse import invoke_json
from lyriclens.rag import prompts


def select_candidates(song: SongInfo, question: str, candidates: list[WikiCandidate],
                      chat) -> set[int]:
    if not candidates:
        return set()
    listing = "\n".join(f"- page_id={c.page_id} | {c.title} | {c.snippet}" for c in candidates)
    messages = [
        SystemMessage(prompts.CANDIDATE_SELECTION_SYSTEM),
        HumanMessage(prompts.CANDIDATE_SELECTION_HUMAN.format(
            title=song.title, artist=song.artist_query, question=question, candidates=listing,
        )),
    ]
    chosen = invoke_json(chat, messages, list) or []
    valid = {c.page_id for c in candidates}
    return {int(x) for x in chosen if isinstance(x, int | str) and str(x).isdigit()} & valid
