"""수집 캐시 — 이미 수집한 (곡, 검색어)와 page_id 를 기록한다 (NF2002)."""

from __future__ import annotations

import json
from pathlib import Path


class CollectCache:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.data: dict[str, dict[str, list]] = (
            json.loads(self.path.read_text(encoding="utf-8")) if self.path.exists() else {}
        )

    def _entry(self, song_id: str) -> dict[str, list]:
        return self.data.setdefault(song_id, {"queries": [], "page_ids": []})

    def has_query(self, song_id: str, query: str) -> bool:
        return query in self.data.get(song_id, {}).get("queries", [])

    def page_ids(self, song_id: str) -> set[int]:
        return set(self.data.get(song_id, {}).get("page_ids", []))

    def primary_done(self, song_id: str) -> bool:
        """1차 문서 수집을 마친 곡 (플래그 없는 이전 캐시는 검색어 기록이 있으면 마친 것)."""
        entry = self.data.get(song_id, {})
        return bool(entry.get("primary_done") or entry.get("queries"))

    def mark_primary_done(self, song_id: str) -> None:
        self._entry(song_id)["primary_done"] = True
        self._save()

    def add(self, song_id: str, queries: list[str], page_ids: list[int]) -> None:
        entry = self._entry(song_id)
        entry["queries"] += [q for q in queries if q not in entry["queries"]]
        entry["page_ids"] += [p for p in page_ids if p not in entry["page_ids"]]
        self._save()

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.data, ensure_ascii=False, indent=1),
                             encoding="utf-8")
