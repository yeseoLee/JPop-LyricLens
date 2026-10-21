"""유사도 검색과 MMR 의 근거 목록 비교 (SPEC-017, F2014).

    python scripts/compare_retrieval.py [--show 3]
QA 벤치마크의 답할 수 있는 질문마다 두 방식으로 근거를 모아 다양성을 요약하고,
앞의 몇 질문은 근거 목록을 나란히 보여 준다.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from lyriclens.bench.cases import load_qa_cases  # noqa: E402
from lyriclens.bench.diversity import diversity_summary  # noqa: E402
from lyriclens.config import load_settings  # noqa: E402
from lyriclens.domain.crawl import read_songs  # noqa: E402
from lyriclens.index.store import VectorStore  # noqa: E402
from lyriclens.llm import make_embeddings  # noqa: E402
from lyriclens.rag.retrieve import retrieve  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--show", type=int, default=3)
    args = parser.parse_args()
    base = load_settings()
    modes = {
        "similarity": load_settings(overrides={"retrieval": {**base.retrieval,
                                                             "search_type": "similarity"}}),
        "mmr": load_settings(overrides={"retrieval": {**base.retrieval, "search_type": "mmr"}}),
    }
    emb = make_embeddings(base)
    store = VectorStore(base.path("chroma"), emb)
    songs = {(s.title, s.artist): s.song_id for s in read_songs(base.path("songs"))}
    cases = [c for c in load_qa_cases(ROOT / "bench/qa_cases.yaml") if c["type"] != "unanswerable"]
    totals = {m: {"distinct_docs": 0, "sim": [], "n": 0} for m in modes}
    for i, case in enumerate(cases):
        sid = songs[(case["song"]["title"], case["song"]["artist"])]
        lists = {m: retrieve(store, sid, case["question"], s) for m, s in modes.items()}
        for m, ev in lists.items():
            d = diversity_summary(ev, emb)
            totals[m]["distinct_docs"] += d["distinct_docs"]
            totals[m]["n"] += 1
            if d["mean_pairwise_sim"] is not None:
                totals[m]["sim"].append(d["mean_pairwise_sim"])
        if i < args.show:
            print(f"\n[{case['id']}] {case['question']}")
            for m, ev in lists.items():
                wiki = [f"{e.title}" for e in ev if e.source_type == "wikipedia"]
                print(f"  {m:10s} 위키 근거: {wiki}")
    print("\n| 방식 | 질문당 서로 다른 위키 문서 수 | 위키 근거 평균 쌍별 유사도 | 질문 수 |")
    print("|---|---|---|---|")
    for m, t in totals.items():
        mean_sim = round(sum(t["sim"]) / len(t["sim"]), 4) if t["sim"] else "-"
        print(f"| {m} | {round(t['distinct_docs'] / t['n'], 2)} | {mean_sim} | {t['n']} |")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
