"""근거 형식 (SPEC-006 §3)."""

from __future__ import annotations

from dataclasses import dataclass, field

SOURCE_LABELS = {"song_meta": "곡 정보", "lyrics": "가사", "wikipedia": "위키백과"}


@dataclass
class Evidence:
    num: int
    chunk_id: str
    source_type: str
    title: str
    url: str
    text: str
    metadata: dict = field(default_factory=dict)

    @property
    def label(self) -> str:
        return SOURCE_LABELS.get(self.source_type, self.source_type)
