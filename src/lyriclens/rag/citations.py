"""답변 본문의 근거 표기 파싱과 인용 근거 선택 (SPEC-007 §3.4, F2008)."""

from __future__ import annotations

import re

from lyriclens.domain.lyrics import quote_lines
from lyriclens.rag.evidence import Evidence

MARKER = re.compile(r"\[(?:근거|Source|source|根拠)\s*([\d,\s]+)\]")
PREVIEW_CHARS = 200


def cited_numbers(text: str) -> list[int]:
    nums: list[int] = []
    for m in MARKER.finditer(text):
        for part in m.group(1).split(","):
            part = part.strip()
            if part.isdigit() and int(part) not in nums:
                nums.append(int(part))
    return nums


def select_cited(evidence: list[Evidence], text: str) -> list[Evidence]:
    wanted = set(cited_numbers(text))
    return [e for e in evidence if e.num in wanted]


def preview(ev: Evidence, max_lines: int) -> str:
    if ev.source_type == "lyrics":
        return quote_lines(ev.text, max_lines)
    text = " ".join(ev.text.split())
    return text if len(text) <= PREVIEW_CHARS else text[:PREVIEW_CHARS] + "…"
