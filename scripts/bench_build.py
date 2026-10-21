"""벤치마크 케이스 검증과 가사 질의 생성 (SPEC-015 §5).

    python scripts/bench_build.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from langchain_core.messages import HumanMessage, SystemMessage  # noqa: E402

from lyriclens.bench.cases import (  # noqa: E402
    load_lyric_refs,
    load_qa_cases,
    load_search_cases,
    lyric_line,
    resolve_cases,
    validate_cases,
)
from lyriclens.config import load_settings  # noqa: E402
from lyriclens.domain.crawl import read_songs  # noqa: E402
from lyriclens.llm import make_chat  # noqa: E402
from lyriclens.rag import prompts  # noqa: E402

QUERIES = ROOT / "data" / "bench" / "lyric_queries.json"
LANGUAGE = {"ko": "한국어", "en": "English"}
KANA = re.compile(r"[\u3040-\u30ff]")
HANGUL = re.compile(r"[\uac00-\ud7a3]")


def clean_translation(text: str, lang: str) -> bool:
    """대상 언어로만 옮겼는지 (가나가 남거나, 영어에 한글이 섞이면 실패)."""
    return not KANA.search(text) and not (lang == "en" and HANGUL.search(text))


def main() -> int:
    settings = load_settings()
    search = load_search_cases(ROOT / "bench/search_cases.yaml")
    refs = load_lyric_refs(ROOT / "bench/lyric_refs.yaml")
    qa = load_qa_cases(ROOT / "bench/qa_cases.yaml")
    errors = validate_cases(search, refs, qa)
    songs = [s.to_dict() for s in read_songs(settings.path("songs"))]
    _, missing = resolve_cases(search + [{"id": q["id"], "relevant": [q["song"]]} for q in qa],
                               songs)
    for e in errors + missing:
        print("오류:", e)
    if errors or missing:
        return 1

    by_key = {(s["title"], s["artist"]): s for s in songs}
    queries = json.loads(QUERIES.read_text(encoding="utf-8")) if QUERIES.exists() else {}
    chat, strong = make_chat(settings, aux=True), make_chat(settings)
    made = 0
    for r in refs:
        if r["lang"] == "ja":
            continue
        if r["id"] in queries and clean_translation(queries[r["id"]], r["lang"]):
            continue  # 한 번 만든 질의는 고정
        line = lyric_line(by_key[(r["song"]["title"], r["song"]["artist"])], r["stanza"],
                          r["line"])
        system = prompts.BENCH_TRANSLATE_SYSTEM.format(language=LANGUAGE[r["lang"]])
        messages = [SystemMessage(system), HumanMessage(line)]
        text = chat.invoke(messages).content.strip()
        if not clean_translation(text, r["lang"]):  # 섞인 번역은 주 모델로 다시
            text = strong.invoke(messages).content.strip()
        queries[r["id"]] = text
        made += 1
    QUERIES.parent.mkdir(parents=True, exist_ok=True)
    QUERIES.write_text(json.dumps(queries, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"케이스 검증 통과: 곡 찾기 {len(search)} + 가사 {len(refs)}, QA {len(qa)}")
    print(f"가사 번역 질의: 새로 {made}개, 전체 {len(queries)}개 → {QUERIES}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
