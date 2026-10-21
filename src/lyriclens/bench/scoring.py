"""답변 채점 — 정답 키워드와 LLM 판정 (SPEC-015 §4.2, D-12)."""

from __future__ import annotations

import re
import unicodedata

from lyriclens.jsonparse import parse_json

VERDICTS = {"correct", "incorrect", "abstain"}


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).casefold()
    return re.sub(r"\s+", "", text)


def _contains(text: str, keyword: str) -> bool:
    """숫자로 끝나는(시작하는) 키워드는 바로 뒤(앞)에 숫자가 붙으면 안 된다.
    공백을 지운 뒤라 'october2' 가 'october21' 안에서 맞는 일을 막는다."""
    if not keyword:
        return False
    before = r"(?<!\d)" if keyword[0].isdigit() else ""
    after = r"(?!\d)" if keyword[-1].isdigit() else ""
    return re.search(before + re.escape(keyword) + after, text) is not None


def keyword_correct(answer: str, groups: list[list[str]]) -> bool:
    norm = normalize(answer)
    return all(any(_contains(norm, normalize(k)) for k in group) for group in groups)


def parse_judgement(text: str) -> str:
    try:
        data = parse_json(text)
    except ValueError:
        return "unknown"
    verdict = str(data.get("verdict", "")).strip().lower() if isinstance(data, dict) else ""
    return verdict if verdict in VERDICTS else "unknown"
