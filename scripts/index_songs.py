"""data/songs.jsonl → Chroma song_meta / song_lyrics 색인 (SPEC-003).

    python scripts/index_songs.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lyriclens.config import load_settings  # noqa: E402
from lyriclens.domain.crawl import read_songs  # noqa: E402
from lyriclens.domain.indexing import index_songs  # noqa: E402
from lyriclens.index.store import VectorStore  # noqa: E402
from lyriclens.llm import MissingKeyError, make_embeddings  # noqa: E402


def main() -> int:
    settings = load_settings()
    songs = read_songs(settings.path("songs"))
    if not songs:
        print("수집된 곡이 없습니다. 먼저 python scripts/crawl_songs.py 를 실행하세요.")
        return 1
    try:
        embeddings = make_embeddings(settings)
    except MissingKeyError as exc:
        print(f"{exc} .env 를 확인하세요.")
        return 1
    store = VectorStore(settings.path("chroma"), embeddings)
    index_songs(
        songs,
        store,
        item_text_max_chars=settings.chunking["item_text_max_chars"],
        lyrics_chunk_lines=settings.chunking["lyrics_chunk_lines"],
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
