"""가사 연(stanza) 분할과 화면 인용 길이 제한 (SPEC-003 §3.2, D-02)."""

from __future__ import annotations


def split_stanzas(lyrics: str, max_lines: int) -> list[str]:
    stanzas: list[list[str]] = [[]]
    for line in lyrics.splitlines():
        if line.strip():
            stanzas[-1].append(line.strip())
        elif stanzas[-1]:
            stanzas.append([])
    out: list[str] = []
    for lines in stanzas:
        for i in range(0, len(lines), max_lines):
            out.append("\n".join(lines[i : i + max_lines]))
    return out


def quote_lines(text: str, max_lines: int) -> str:
    lines = text.splitlines()
    if len(lines) <= max_lines:
        return "\n".join(lines)
    return "\n".join(lines[:max_lines] + ["…"])
