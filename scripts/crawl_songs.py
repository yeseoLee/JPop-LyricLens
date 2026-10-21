"""utaten 수집 → data/songs.jsonl (SPEC-002).

    python scripts/crawl_songs.py [--limit-artists N] [--write-artist-ids]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lyriclens.config import load_artists, load_settings  # noqa: E402
from lyriclens.domain.crawl import crawl_artists, write_songs  # noqa: E402
from lyriclens.domain.utaten_client import UtatenClient  # noqa: E402


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
        body = yaml.safe_dump({"artists": artists}, allow_unicode=True, sort_keys=False)
        path.write_text(header + "\n" + body, encoding="utf-8")
        print(f"아티스트 ID 기록: {path}")


if __name__ == "__main__":
    main()
