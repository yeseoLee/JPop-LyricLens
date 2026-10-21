"""질문 언어 판별 — 한글 → ko, 가나·한자 → ja, 그 밖 → en (SPEC-007 §3.1)."""

from __future__ import annotations

import re

HANGUL = re.compile(r"[가-힣ㄱ-ㆎ]")
JAPANESE = re.compile(r"[぀-ヿ一-鿿]")


def detect_language(text: str) -> str:
    if HANGUL.search(text):
        return "ko"
    if JAPANESE.search(text):
        return "ja"
    return "en"
