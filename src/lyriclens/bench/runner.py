"""벤치마크 실행과 요약 (SPEC-015 §3.5, §5)."""

from __future__ import annotations

import time
from collections.abc import Callable

from lyriclens.bench.metrics import ranking_metrics

METRICS = ["hit@1", "hit@5", "hit@10", "recall@10", "mrr@10", "ndcg@10"]


def _mean(rows: list[dict], key: str) -> float:
    return round(sum(r[key] for r in rows) / len(rows), 4) if rows else 0.0


def _aggregate(rows: list[dict]) -> dict:
    out = {m: _mean(rows, m) for m in METRICS}
    out["n"] = len(rows)
    out["sec/query"] = _mean(rows, "sec")
    return out


def _group(rows: list[dict], key: str) -> dict:
    groups: dict[str, list[dict]] = {}
    for r in rows:
        groups.setdefault(r[key], []).append(r)
    return {k: _aggregate(v) for k, v in sorted(groups.items())}


def run_search(cases: list[dict], systems: dict[str, Callable[[str], list[str]]],
               on_case=lambda system, case, row: None) -> dict:
    """systems: 이름 → (질의 → song_id 순위 목록). 케이스별 행과 요약을 돌려준다."""
    report = {"rows": {}, "summary": {}}
    for name, search in systems.items():
        rows = []
        for case in cases:
            t = time.time()
            try:
                ranked = list(dict.fromkeys(search(case["query"])))
                error = None
            except Exception as exc:  # 한 케이스 실패가 전체를 멈추지 않게
                ranked, error = [], repr(exc)
            row = {"id": case["id"], "category": case["category"], "lang": case["lang"],
                   "split": case["split"], "query": case["query"], "top5": ranked[:5],
                   "sec": time.time() - t, "error": error,
                   **ranking_metrics(ranked, set(case["relevant_ids"]))}
            rows.append(row)
            on_case(name, case, row)
        report["rows"][name] = rows
        report["summary"][name] = {
            "all": _aggregate(rows),
            "by_category": _group(rows, "category"),
            "by_lang": _group(rows, "lang"),
            "by_split": _group(rows, "split"),
        }
    return report


def _table(header: list[str], lines: list[list]) -> str:
    out = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    out += ["| " + " | ".join(str(c) for c in line) + " |" for line in lines]
    return "\n".join(out)


def summary_markdown(report: dict) -> str:
    summary = report["summary"]
    parts = ["### 전체", _table(["시스템", *METRICS, "n", "초/질의"], [
        [name, *[s["all"][m] for m in METRICS], s["all"]["n"], s["all"]["sec/query"]]
        for name, s in summary.items()
    ])]
    for group, title in (("by_category", "범주별 MRR@10"), ("by_lang", "언어별 MRR@10"),
                         ("by_split", "split별 MRR@10")):
        keys = sorted({k for s in summary.values() for k in s[group]})
        parts += [f"### {title}", _table(["시스템", *keys], [
            [name, *[s[group].get(k, {}).get("mrr@10", "-") for k in keys]]
            for name, s in summary.items()
        ])]
    return "\n\n".join(parts)
