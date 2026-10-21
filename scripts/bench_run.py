"""벤치마크 실행 (SPEC-015 §5).

    python scripts/bench_run.py search [--systems meta_vector lyrics_vector ...] [--split dev|test]
    python scripts/bench_run.py qa [--modes rag norag] [--split dev|test]
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from lyriclens.bench.cases import (  # noqa: E402
    load_lyric_refs,
    load_qa_cases,
    load_search_cases,
    materialize_lyric_queries,
    resolve_cases,
)
from lyriclens.bench.qa import norag_answer, qa_markdown, run_qa  # noqa: E402
from lyriclens.bench.runner import run_search, summary_markdown  # noqa: E402
from lyriclens.bench.systems import build_search_systems  # noqa: E402
from lyriclens.collect.cache import CollectCache  # noqa: E402
from lyriclens.collect.wikipedia import WikiClient  # noqa: E402
from lyriclens.config import load_settings  # noqa: E402
from lyriclens.domain.crawl import read_songs  # noqa: E402
from lyriclens.index.store import VectorStore  # noqa: E402
from lyriclens.llm import make_chat, make_embeddings  # noqa: E402
from lyriclens.ui.service import LyricLensService  # noqa: E402

RESULTS = ROOT / "data" / "bench" / "results"


def _save(kind: str, report: dict) -> Path:
    RESULTS.mkdir(parents=True, exist_ok=True)
    path = RESULTS / f"{datetime.now():%Y%m%d-%H%M%S}-{kind}.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=1, default=str),
                    encoding="utf-8")
    return path


def search_cases(settings, songs, split):
    cases, missing = resolve_cases(load_search_cases(ROOT / "bench/search_cases.yaml"), songs)
    qpath = ROOT / "data" / "bench" / "lyric_queries.json"
    translations = json.loads(qpath.read_text(encoding="utf-8")) if qpath.exists() else {}
    lyric, lmissing = materialize_lyric_queries(load_lyric_refs(ROOT / "bench/lyric_refs.yaml"),
                                                songs, translations)
    if missing or lmissing:
        print("빠진 케이스(bench_build.py 를 먼저 실행):", missing + lmissing)
    cases += lyric
    return [c for c in cases if split in (None, c["split"])]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("kind", choices=["search", "qa"])
    parser.add_argument("--systems", nargs="*")
    parser.add_argument("--modes", nargs="*", default=["rag", "norag"])
    parser.add_argument("--split", choices=["dev", "test"])
    args = parser.parse_args()

    settings = load_settings()
    songs = [s.to_dict() for s in read_songs(settings.path("songs"))]
    store = VectorStore(settings.path("chroma"), make_embeddings(settings))
    aux = make_chat(settings, aux=True)

    def progress(name, case, row):
        flag = row.get("error") or ""
        print(f"  [{name}] {case['id']} {flag}", flush=True)

    if args.kind == "search":
        cases = search_cases(settings, songs, args.split)
        report = run_search(cases, build_search_systems(store, aux, settings, args.systems),
                            on_case=progress)
        md = summary_markdown(report)
    else:
        by_key = {(s["title"], s["artist"]): s for s in songs}
        cases = []
        for q in load_qa_cases(ROOT / "bench/qa_cases.yaml"):
            if args.split and q["split"] != args.split:
                continue
            song = by_key[(q["song"]["title"], q["song"]["artist"])]
            cases.append({**q, "song_id": song["song_id"], "song_title": song["title"],
                          "song_artist": song["artist"]})
        chat = make_chat(settings)
        service = LyricLensService(settings, store, chat,
                                   WikiClient(contact=settings.wiki_contact),
                                   CollectCache(settings.path("collect_cache")), aux_chat=aux)
        modes = {
            "rag": lambda c: service.ask(c["song_id"], c["question"], []).answer.text,
            "norag": lambda c: norag_answer(c, chat),
        }
        judge = make_chat(load_settings(overrides={
            "llm": {"chat_model": settings.bench.get("judge_model", "gpt-6-luna")}}))
        report = run_qa(cases, {m: modes[m] for m in args.modes}, judge, on_case=progress)
        md = qa_markdown(report)
    path = _save(args.kind, report)
    print(md)
    print(f"\n결과 저장: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
