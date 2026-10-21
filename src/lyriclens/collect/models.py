"""수집 영역 데이터 형식 (SPEC-004 §3.1). collect/ 는 도메인 모델(Song)을 직접 쓰지 않는다."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SongInfo:
    song_id: str
    title: str
    artist: str
    artist_ko: str | None = None
    tieup: str | None = None

    @property
    def artist_query(self) -> str:
        return self.artist_ko or self.artist


@dataclass
class WikiCandidate:
    page_id: int
    title: str
    snippet: str


@dataclass
class WikiPage:
    page_id: int
    title: str
    url: str
    text: str


@dataclass
class CollectedDoc:
    page: WikiPage
    query: str
    is_primary: bool


@dataclass
class CollectResult:
    queries: list[str] = field(default_factory=list)
    indexed: list[CollectedDoc] = field(default_factory=list)
    discarded: list[WikiCandidate] = field(default_factory=list)
    cached_queries: list[str] = field(default_factory=list)
