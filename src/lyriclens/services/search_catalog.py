"""곡 카탈로그 — 제목·아티스트·별칭 이름표와 어휘·퍼지 일치 (SPEC-016 §2.2 lexical, §2.3)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from lyriclens.services.search_text import kana_to_romaji, normalize_query, similarity

PAREN = re.compile(r"\s*[\(（\[［].*?[\)）\]］]\s*")
ARTIST_FACTOR = 0.95  # 아티스트 일치는 제목 일치보다 살짝 아래


@dataclass
class Match:
    song_id: str
    score: float
    reasons: list[str] = field(default_factory=list)


@dataclass
class _Entry:
    norm: str
    label: str
    kind: str      # "title" | "artist"
    target: str    # song_id 또는 artist


class Catalog:
    def __init__(self, metas: list[dict], entries: list[_Entry]):
        self.metas = {m["song_id"]: m for m in metas}
        self.by_artist: dict[str, list[str]] = {}
        for m in metas:
            self.by_artist.setdefault(m["artist"], []).append(m["song_id"])
        self.entries = entries

    @classmethod
    def build(cls, metas: list[dict], artist_aliases: dict[str, list[str]],
              title_aliases: dict[str, list[str]]) -> Catalog:
        entries: list[_Entry] = []

        def add(name: str, kind: str, target: str) -> None:
            norm = normalize_query(name or "")
            if norm and not any(e.norm == norm and e.target == target for e in entries):
                entries.append(_Entry(norm, name, kind, target))

        for m in metas:
            sid, title = m["song_id"], m["title"]
            add(title, "title", sid)
            add(PAREN.sub(" ", title).strip(), "title", sid)
            kana = m.get("title_kana")
            if kana:
                add(kana, "title", sid)
                add(kana_to_romaji(normalize_query(kana)), "title", sid)
            for alias in title_aliases.get(sid, []):
                add(alias, "title", sid)
        for artist in {m["artist"] for m in metas}:
            add(artist, "artist", artist)
            for alias in artist_aliases.get(artist, []):
                add(alias, "artist", artist)
            for m in metas:  # 아티스트 한국어 표기도 이름표로
                if m["artist"] == artist and m.get("artist_ko"):
                    add(m["artist_ko"], "artist", artist)
                    break
        return cls(metas, entries)

    def _best(self, norm: str, kind: str, threshold: float) -> dict[str, tuple[float, str]]:
        best: dict[str, tuple[float, str]] = {}
        for e in self.entries:
            if e.kind != kind:
                continue
            score = similarity(norm, e.norm)
            if score >= threshold and score > best.get(e.target, (0, ""))[0]:
                best[e.target] = (score, e.label)
        return best

    def match(self, query: str, threshold: float = 0.75) -> list[Match]:
        """질의 전체와, 공백으로 나눈 앞/뒤 조합을 제목·아티스트에 맞춘다."""
        results: dict[str, Match] = {}

        def put(sid: str, score: float, reason: str) -> None:
            cur = results.get(sid)
            if cur is None or score > cur.score:
                results[sid] = Match(sid, score, [reason])

        whole = normalize_query(query)
        for sid, (score, label) in self._best(whole, "title", threshold).items():
            put(sid, score, f"제목 일치: {label}")
        for artist, (score, label) in self._best(whole, "artist", threshold).items():
            for sid in self.by_artist.get(artist, []):
                put(sid, score * ARTIST_FACTOR, f"아티스트 일치: {label} → {artist}")

        tokens = query.split()
        for i in range(1, len(tokens)):  # 혼합 질의: 앞/뒤 중 하나는 아티스트, 하나는 제목
            for a_part, t_part in ((tokens[:i], tokens[i:]), (tokens[i:], tokens[:i])):
                artists = self._best(normalize_query(" ".join(a_part)), "artist", threshold)
                titles = self._best(normalize_query(" ".join(t_part)), "title", threshold)
                for sid, (t_score, t_label) in titles.items():
                    artist = self.metas[sid]["artist"]
                    if artist in artists:
                        a_score, a_label = artists[artist]
                        put(sid, 1.0 + min(t_score, a_score) / 10,
                            f"아티스트+제목 일치: {a_label} / {t_label}")
        return sorted(results.values(), key=lambda m: -m.score)


def validate_aliases(aliases: dict[str, list[str]], artists: list[str]) -> list[str]:
    keys = {normalize_query(a) for a in aliases}  # '藤井風' 과 '藤井 風' 은 같은 아티스트
    errors = [f"{a}: 별칭 항목 없음" for a in artists if normalize_query(a) not in keys]
    owner: dict[str, str] = {}
    for artist, names in aliases.items():
        for name in [artist, *names]:
            norm = normalize_query(name)
            if norm in owner and owner[norm] != artist:
                errors.append(f"'{name}': {owner[norm]} 와 {artist} 에 겹침")
            owner.setdefault(norm, artist)
    return errors
