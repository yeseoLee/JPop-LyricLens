"""곡 240개 전체의 한국어·영어·로마자 제목 별칭 생성 → config/title_aliases.yaml (SPEC-016 §2.3).

    python scripts/build_title_aliases.py      # 이미 있는 곡은 건너뛴다
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from langchain_core.messages import HumanMessage, SystemMessage  # noqa: E402

from lyriclens.config import load_settings  # noqa: E402
from lyriclens.domain.crawl import read_songs  # noqa: E402
from lyriclens.jsonparse import invoke_json  # noqa: E402
from lyriclens.llm import make_chat  # noqa: E402
from lyriclens.rag import prompts  # noqa: E402

HEADER = ("# 곡 제목 별칭 (SPEC-016 §2.3). scripts/build_title_aliases.py 가 곡 240개 전체를\n"
          "# 같은 방식으로 생성한다 (특정 벤치마크 케이스에 맞추지 않음). 키: song_id\n")


def main() -> int:
    settings = load_settings()
    path = settings.path("title_aliases")
    data = (yaml.safe_load(path.read_text(encoding="utf-8")) or {}) if path.exists() else {}
    aliases: dict[str, list[str]] = data.get("aliases") or {}
    chat = make_chat(settings)
    songs = read_songs(settings.path("songs"))
    for i, song in enumerate(songs, start=1):
        if song.song_id in aliases:
            continue
        human = f"제목: {song.title}\n아티스트: {song.artist}"
        result = invoke_json(chat, [SystemMessage(prompts.TITLE_ALIAS_SYSTEM),
                                    HumanMessage(human)], list) or []
        aliases[song.song_id] = [str(a).strip() for a in result
                                 if str(a).strip() and str(a).strip() != song.title][:6]
        print(f"[{i}/{len(songs)}] {song.title}: {aliases[song.song_id]}", flush=True)
        if i % 20 == 0:  # 중간 저장
            path.write_text(HEADER + yaml.safe_dump({"aliases": aliases}, allow_unicode=True,
                                                    sort_keys=False, width=200),
                            encoding="utf-8")
    path.write_text(HEADER + yaml.safe_dump({"aliases": aliases}, allow_unicode=True,
                                            sort_keys=False, width=200), encoding="utf-8")
    print(f"제목 별칭: {len(aliases)}곡 → {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
