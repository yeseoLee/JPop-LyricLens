"""곡 데이터 모델 (docs/SPEC.md §3.1)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, fields


@dataclass
class Song:
    song_id: str
    title: str
    artist: str
    lyrics: str
    url: str
    title_kana: str | None = None
    artist_ko: str | None = None
    lyricist: str | None = None
    composer: str | None = None
    arranger: str | None = None
    release_date: str | None = None
    tieup: str | None = None
    lyrics_kana: str = ""
    lyrics_romaji: str | None = None
    crawled_at: str | None = None

    @property
    def release_year(self) -> int | None:
        return int(self.release_date[:4]) if self.release_date else None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> Song:
        names = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in data.items() if k in names})
