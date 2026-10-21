"""순위 지표 — 이진 관련도 기준 (SPEC-015 §3.5)."""

from __future__ import annotations

import math


def hit_at_k(ranked: list[str], relevant: set[str], k: int) -> float:
    return 1.0 if relevant & set(ranked[:k]) else 0.0


def recall_at_k(ranked: list[str], relevant: set[str], k: int) -> float:
    if not relevant:
        return 0.0
    return len(relevant & set(ranked[:k])) / min(len(relevant), k)


def mrr_at_k(ranked: list[str], relevant: set[str], k: int = 10) -> float:
    for i, item in enumerate(ranked[:k], start=1):
        if item in relevant:
            return 1.0 / i
    return 0.0


def ndcg_at_k(ranked: list[str], relevant: set[str], k: int = 10) -> float:
    dcg = sum(1.0 / math.log2(i + 1) for i, item in enumerate(ranked[:k], start=1)
              if item in relevant)
    ideal = sum(1.0 / math.log2(i + 1) for i in range(1, min(len(relevant), k) + 1))
    return dcg / ideal if ideal else 0.0


def ranking_metrics(ranked: list[str], relevant: set[str]) -> dict[str, float]:
    return {
        "hit@1": hit_at_k(ranked, relevant, 1),
        "hit@5": hit_at_k(ranked, relevant, 5),
        "hit@10": hit_at_k(ranked, relevant, 10),
        "recall@10": recall_at_k(ranked, relevant, 10),
        "mrr@10": mrr_at_k(ranked, relevant, 10),
        "ndcg@10": ndcg_at_k(ranked, relevant, 10),
    }
