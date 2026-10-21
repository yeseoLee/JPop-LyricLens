"""가사 구절 해석 — 구절이 든 연 + 곡 정보 + 위키 근거로 번역·풀이·배경 (SPEC-009 §3.1)."""

from __future__ import annotations

from dataclasses import dataclass, field

from langchain_core.messages import HumanMessage, SystemMessage

from lyriclens.domain.lyrics import quote_lines
from lyriclens.index.store import IndexDoc
from lyriclens.jsonparse import invoke_json
from lyriclens.rag import prompts
from lyriclens.rag.citations import select_cited
from lyriclens.rag.evidence import Evidence
from lyriclens.rag.generate import format_evidence
from lyriclens.rag.retrieve import SONG_LYRICS, SONG_META, WIKI_DOCS, evidence_title


@dataclass
class Interpretation:
    status: str
    original: str = ""
    translation: str = ""
    notes: list[str] = field(default_factory=list)
    background: str = ""
    citations: list[Evidence] = field(default_factory=list)


def _squash(text: str) -> str:
    return "".join(text.split())


def find_stanza(store, song_id: str, phrase: str) -> IndexDoc | None:
    target = _squash(phrase)
    if not target:
        return None
    stanzas = store.get_where(SONG_LYRICS, {"song_id": song_id})
    stanzas.sort(key=lambda d: d.metadata.get("stanza_seq", 0))
    joined = [(d, _squash(d.text)) for d in stanzas]
    for doc, text in joined:
        if target in text:
            return doc
    # 여러 연에 걸친 구절은 첫 줄이 든 연으로 본다
    first = _squash(phrase.strip().splitlines()[0])
    return next((doc for doc, text in joined if first and first in text), None)


def interpret_phrase(song_id: str, phrase: str, target_lang: str, store, chat,
                     settings) -> Interpretation:
    stanza = find_stanza(store, song_id, phrase)
    if stanza is None:
        return Interpretation(status="not_found")

    rows = [(d, "song_meta") for d in store.get(SONG_META, [song_id])]
    rows.append((stanza, "lyrics"))
    rows += [(d, "wikipedia") for d, _ in store.search(
        WIKI_DOCS, phrase, settings.retrieval["wiki_top_k"], {"song_id": song_id})]
    evidence = [
        Evidence(n, d.id, t, evidence_title(d, t), d.metadata.get("url", ""), d.text, d.metadata)
        for n, (d, t) in enumerate(rows, start=1)
    ]
    max_lines = settings.display["lyrics_quote_max_lines"]
    system = prompts.INTERPRET_SYSTEM.format(
        language=prompts.TARGET_LANGUAGES.get(target_lang, "한국어"), quote_max_lines=max_lines
    )
    human = prompts.INTERPRET_HUMAN.format(evidence=format_evidence(evidence), phrase=phrase)
    data = invoke_json(chat, [SystemMessage(system), HumanMessage(human)], dict) or {}

    notes = [str(n) for n in data.get("notes", []) if n] if isinstance(data.get("notes"), list) \
        else []
    result = Interpretation(
        status="ok",
        original=quote_lines(phrase.strip(), max_lines),
        translation=str(data.get("translation", "")),
        notes=notes,
        background=str(data.get("background", "")),
    )
    result.citations = select_cited(
        evidence, " ".join([result.translation, *result.notes, result.background])
    )
    return result
