"""근거 다양성 요약 — 유사도 검색과 MMR 비교용 (SPEC-017)."""

from __future__ import annotations

from itertools import combinations


def diversity_summary(evidence, embeddings) -> dict:
    """위키 근거의 서로 다른 문서 수와, 근거 청크끼리의 평균 코사인 유사도(낮을수록 다양)."""
    wiki = [e for e in evidence if e.source_type == "wikipedia"]
    vecs = embeddings.embed_documents([e.text for e in wiki]) if len(wiki) > 1 else []
    units = []
    for v in vecs:
        norm = sum(x * x for x in v) ** 0.5 or 1.0
        units.append([x / norm for x in v])
    pairs = [sum(x * y for x, y in zip(a, b, strict=True)) for a, b in combinations(units, 2)]
    return {
        "wiki_evidence": len(wiki),
        "distinct_docs": len({e.metadata.get("doc_id") for e in wiki}),
        "mean_pairwise_sim": round(sum(pairs) / len(pairs), 4) if pairs else None,
    }
