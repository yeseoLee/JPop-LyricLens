"""utaten 수집 → data/songs.jsonl (SPEC-002).

    python scripts/crawl_songs.py [--limit-artists N] [--write-artist-ids]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lyriclens.config import load_artists, load_settings  # noqa: E402
from lyriclens.domain.crawl import crawl_artists, write_songs  # noqa: E402
from lyriclens.domain.utaten_client import UtatenClient  # noqa: E402


def format_artists(artists: list[dict]) -> str:
    """artists.yaml 의 기존 형식(따옴표 문자열, 2칸 들여쓰기)을 유지해 diff를 ID 변경으로 한정한다."""
    lines = ["artists:"]
    for a in artists:
        artist_id = a.get("utaten_artist_id")
        quoted = f'"{artist_id}"' if artist_id else "null"
        lines += [
            f'  - name: "{a["name"]}"',
            f'    name_ko: "{a["name_ko"]}"',
            f"    utaten_artist_id: {quoted}",
        ]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit-artists", type=int, default=None)
    parser.add_argument("--write-artist-ids", action="store_true")
    args = parser.parse_args()

    settings = load_settings()
    artists = load_artists()
    targets = artists[: args.limit_artists] if args.limit_artists else artists
    client = UtatenClient(
        interval_sec=settings.crawl["request_interval_sec"],
        max_retries=settings.crawl["max_retries"],
        contact=settings.wiki_contact,
        cache_dir=settings.path("raw_html"),
    )
    result = crawl_artists(targets, client, settings.crawl["songs_per_artist"])
    write_songs(result.songs, settings.path("songs"))
    for name in result.skipped:
        print(f"아티스트를 찾지 못함: {name}")
    for err in result.errors:
        print(f"오류: {err}")

    if args.write_artist_ids:
        path = settings.path("artists")
        header = path.read_text(encoding="utf-8").splitlines()[0]
        path.write_text(header + "\n" + format_artists(artists), encoding="utf-8")
        print(f"아티스트 ID 기록: {path}")


if __name__ == "__main__":
    main()
