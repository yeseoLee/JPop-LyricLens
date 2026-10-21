"""프롬프트 3으로 근거 기반 답변 생성 (SPEC-007 §3.3, F2007)."""

from __future__ import annotations

from dataclasses import dataclass, field

from langchain_core.messages import HumanMessage, SystemMessage

from lyriclens.rag import prompts
from lyriclens.rag.citations import select_cited
from lyriclens.rag.evidence import Evidence
from lyriclens.rag.language import detect_language

HISTORY_LIMIT = 4


@dataclass
class Answer:
    text: str
    cited: list[Evidence] = field(default_factory=list)
    no_citation: bool = True


def format_evidence(evidence: list[Evidence]) -> str:
    return "\n\n".join(f"[근거 {e.num}] ({e.label}) {e.title}\n{e.text}" for e in evidence)


def _format_history(history) -> str:
    recent = list(history or [])[-HISTORY_LIMIT:]
    return "\n".join(f"{role}: {content}" for role, content in recent) or "(없음)"


def generate_answer(question: str, evidence: list[Evidence], chat, settings,
                    history=()) -> Answer:
    lang = detect_language(question)
    if not evidence:
        return Answer(prompts.NOT_FOUND[lang])
    language = prompts.LANGUAGE_NAMES[lang]
    system = prompts.ANSWER_SYSTEM.format(
        quote_max_lines=settings.display["lyrics_quote_max_lines"], language=language
    )
    human = prompts.ANSWER_HUMAN.format(
        history=_format_history(history), evidence=format_evidence(evidence), question=question,
        language=language,
    )
    text = chat.invoke([SystemMessage(system), HumanMessage(human)]).content
    cited = select_cited(evidence, text)
    return Answer(text, cited, no_citation=not cited)
