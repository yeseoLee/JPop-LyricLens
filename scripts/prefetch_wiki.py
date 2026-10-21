"""곡·아티스트 위키 문서(1차 문서) 미리 수집 — 첫 질문 시간 단축용, 선택 실행 (SPEC-014).

    python scripts/prefetch_wiki.py [--limit N]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lyriclens.collect.cache import CollectCache  # noqa: E402
from lyriclens.collect.models import SongInfo  # noqa: E402
from lyriclens.collect.prefetch import prefetch_primary  # noqa: E402
from lyriclens.collect.wikipedia import WikiClient  # noqa: E402
from lyriclens.config import load_settings  # noqa: E402
from lyriclens.domain.crawl import read_songs  # noqa: E402
from lyriclens.index.store import VectorStore  # noqa: E402
from lyriclens.llm import make_embeddings  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()
    settings = load_settings()
    songs = [SongInfo(s.song_id, s.title, s.artist, s.artist_ko, s.tieup)
             for s in read_songs(settings.path("songs"))][: args.limit]
    wiki = WikiClient(contact=settings.wiki_contact,
                      interval_sec=settings.collect["request_interval_sec"],
                      max_retries=settings.collect["max_retries"])
    store = VectorStore(settings.path("chroma"), make_embeddings(settings))
    done = prefetch_primary(
        songs, wiki, CollectCache(settings.path("collect_cache")), store, settings,
        on_song=lambda song, n: print(f"{song.title}: 청크 {n}개"),
    )
    print(f"1차 문서 미리 수집: {done}곡 (이미 수집한 곡은 건너뜀)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
