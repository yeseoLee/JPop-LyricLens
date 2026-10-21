"""답변 채점 — 정답 키워드와 LLM 판정 (SPEC-015 §4.2, D-12)."""

from __future__ import annotations

import re
import unicodedata

from lyriclens.jsonparse import parse_json

VERDICTS = {"correct", "incorrect", "abstain"}


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).casefold()
    return re.sub(r"\s+", "", text)


def keyword_correct(answer: str, groups: list[list[str]]) -> bool:
    norm = normalize(answer)
    return all(any(normalize(k) in norm for k in group) for group in groups)


def parse_judgement(text: str) -> str:
    try:
        data = parse_json(text)
    except ValueError:
        return "unknown"
    verdict = str(data.get("verdict", "")).strip().lower() if isinstance(data, dict) else ""
    return verdict if verdict in VERDICTS else "unknown"
