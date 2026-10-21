"""아티스트 목록 → 곡 수집 (SPEC-002 §3.4)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

from lyriclens.domain.models import Song
from lyriclens.domain.utaten_client import FetchError
from lyriclens.domain.utaten_parser import (
    ParseError,
    parse_artist_song_ids,
    parse_search_artists,
    parse_song,
)

MIN_SONGS = 100


@dataclass
class CrawlResult:
    songs: list[Song] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)


def _norm(name: str) -> str:
    return "".join(name.split()).casefold()


def resolve_artist_id(name: str, client) -> str | None:
    html = client.get(f"/search?artist_name={quote(name)}")
    for found_name, artist_id in parse_search_artists(html):
        if _norm(found_name) == _norm(name):
            return artist_id
    return None


def crawl_artists(artists: list[dict], client, songs_per_artist: int) -> CrawlResult:
    """artists 의 utaten_artist_id 가 비어 있으면 찾아서 채운다 (호출자가 저장 여부 결정)."""
    result = CrawlResult()
    seen: set[str] = set()
    for artist in artists:
        name = artist["name"]
        try:
            artist_id = artist.get("utaten_artist_id") or resolve_artist_id(name, client)
        except FetchError as exc:
            result.errors.append(f"{name}: {exc}")
            continue
        if not artist_id:
            result.skipped.append(name)
            continue
        artist["utaten_artist_id"] = str(artist_id)

        try:
            lyric_ids = parse_artist_song_ids(client.get(f"/artist/lyric/{artist_id}"))
        except FetchError as exc:
            result.errors.append(f"{name}: {exc}")
            continue
        for lyric_id in lyric_ids[:songs_per_artist]:
            if f"ut_{lyric_id}" in seen:
                continue
            url = f"https://utaten.com/lyric/{lyric_id}/"
            try:
                song = parse_song(client.get(f"/lyric/{lyric_id}/"), url)
            except (FetchError, ParseError) as exc:
                result.errors.append(f"{lyric_id}: {exc}")
                continue
            song.artist_ko = artist.get("name_ko")
            song.crawled_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
            seen.add(song.song_id)
            result.songs.append(song)
    return result


def write_songs(songs: list[Song], path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for song in songs:
            f.write(json.dumps(song.to_dict(), ensure_ascii=False) + "\n")
    print(f"수집한 곡: {len(songs)}곡 → {path}")
    if len(songs) < MIN_SONGS:
        print(
            f"경고: 곡 수가 {MIN_SONGS}건 미만입니다. "
            "artists.yaml 이나 songs_per_artist 를 늘리세요."
        )


def read_songs(path: str | Path) -> list[Song]:
    path = Path(path)
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as f:
        return [Song.from_dict(json.loads(line)) for line in f if line.strip()]
