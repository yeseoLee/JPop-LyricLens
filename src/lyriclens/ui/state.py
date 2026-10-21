"""화면 상태 — 곡별 대화 기록과 선택 목록 라벨 (SPEC-010 §3.2, F2009)."""

from __future__ import annotations


class ChatStore:
    def __init__(self):
        self._chats: dict[str, list[dict]] = {}

    def messages(self, song_id: str) -> list[dict]:
        return self._chats.setdefault(song_id, [])

    def add(self, song_id: str, role: str, content: str, **extra) -> None:
        self.messages(song_id).append({"role": role, "content": content, **extra})

    def history(self, song_id: str, limit: int = 4) -> list[tuple[str, str]]:
        return [(m["role"], m["content"]) for m in self.messages(song_id)[-limit:]]


def song_label(meta: dict) -> str:
    label = f"{meta.get('title', '')} — {meta.get('artist', '')}"
    year = meta.get("release_year")
    return f"{label} ({year})" if year else label


def song_options(metas: list[dict]) -> list[tuple[str, str]]:
    ordered = sorted(metas, key=lambda m: (m.get("title", "").casefold(), m.get("song_id", "")))
    return [(song_label(m), m["song_id"]) for m in ordered]


def stanza_options(docs) -> list[tuple[str, str]]:
    ordered = sorted(docs, key=lambda d: d.metadata.get("stanza_seq", 0))
    return [(f"{i}. {d.text.splitlines()[0]} …", d.text) for i, d in enumerate(ordered, start=1)]
