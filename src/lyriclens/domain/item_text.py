"""곡 1건 → 색인 텍스트 1개 (docs/SPEC.md §3.3, F2001)."""

from __future__ import annotations

from lyriclens.domain.models import Song


def _join(*parts: str | None, sep: str = " / ") -> str:
    return sep.join(p for p in parts if p)


def build_item_text(song: Song, max_chars: int) -> str:
    title = f"{song.title} ({song.title_kana})" if song.title_kana else song.title
    credits = _join(
        song.lyricist and f"작사: {song.lyricist}",
        song.composer and f"작곡: {song.composer}",
        song.arranger and f"편곡: {song.arranger}",
    )
    header_lines = [
        f"제목: {title}",
        f"아티스트: {_join(song.artist, song.artist_ko)}",
        credits,
        song.release_date and f"발매일: {song.release_date}",
        song.tieup and f"타이업: {song.tieup}",
        "가사:",
    ]
    header = "\n".join(line for line in header_lines if line)
    room = max(max_chars - len(header) - 1, 0)
    return f"{header}\n{song.lyrics[:room]}"[:max_chars]
