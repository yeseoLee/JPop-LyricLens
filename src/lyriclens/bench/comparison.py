"""RAG 사용 전후 비교 보고서 (SPEC-018, F2015)."""

from __future__ import annotations

EXCLUDED_TYPES = {"meaning"}  # 답변에 가사 인용이 많을 수 있어 대표 질문에서 뺀다
ANSWER_CHARS = 300
METRICS = [("kw_acc", "정답률(키워드)"), ("llm_acc", "정답률(LLM)"), ("wrong_rate", "오답률"),
           ("abstain_rate", "모름 인정률"), ("citation_rate", "근거 제시율")]


def truncate(text: str, limit: int = ANSWER_CHARS) -> str:
    text = " ".join((text or "").split())
    return text if len(text) <= limit else text[:limit] + "…"


def _consistent(row: dict) -> bool:
    """키워드 채점과 LLM 판정이 일치하는 문항만 대표로 쓴다."""
    if row["type"] == "unanswerable":
        return row["verdict"] in ("abstain", "incorrect", "correct")
    return row["kw_correct"] == (row["verdict"] == "correct")


def _priority(rag: dict, norag: dict) -> tuple[int, str]:
    if rag["type"] == "unanswerable":
        if rag["verdict"] == "abstain" and norag["verdict"] != "abstain":
            return 1, "RAG만 모른다고 답함"
        return 3, "같음"
    if rag["verdict"] == "correct" and norag["verdict"] != "correct":
        return 0, "RAG만 맞힘"
    if rag["verdict"] == "correct" and norag["verdict"] == "correct":
        return 2, "둘 다 맞힘"
    return 3, "기타"


def pick_examples(report: dict, minimum: int = 8, per_type: int = 2) -> list[dict]:
    rag = {r["id"]: r for r in report["rows"]["rag"]}
    norag = {r["id"]: r for r in report["rows"]["norag"]}
    pool = []
    for qid, r in rag.items():
        n = norag.get(qid)
        if n is None or r["type"] in EXCLUDED_TYPES or not (_consistent(r) and _consistent(n)):
            continue
        prio, label = _priority(r, n)
        pool.append({"id": qid, "type": r["type"], "question": r["question"],
                     "difficulty": r.get("difficulty", "normal"), "priority": prio,
                     "label": label, "rag": r, "norag": n})
    pool.sort(key=lambda p: (p["priority"], p["id"]))
    picked: list[dict] = []
    for t in sorted({p["type"] for p in pool}):  # 유형마다 가장 좋은 예 하나
        picked.append(next(p for p in pool if p["type"] == t))
    for p in pool:  # 우선순위대로 채운다 (유형당 per_type 개까지)
        if len(picked) >= minimum:
            break
        if p not in picked and sum(q["type"] == p["type"] for q in picked) < per_type:
            picked.append(p)
    return sorted(picked, key=lambda p: (p["priority"], p["type"], p["id"]))


def _table(header, lines) -> str:
    out = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    cell = lambda c: "-" if c is None else str(c)  # noqa: E731
    return "\n".join(out + ["| " + " | ".join(cell(c) for c in ln) + " |" for ln in lines])


def comparison_markdown(report: dict, cases: dict[str, dict]) -> str:
    summary = report["summary"]
    parts = ["## 요약", _table(["모드", *[name for _, name in METRICS], "문항"], [
        [m, *[summary[m]["all"][k] for k, _ in METRICS], summary[m]["all"]["n"]]
        for m in ("rag", "norag")])]
    level_header = ["모드", "난이도", *[name for _, name in METRICS[:3]], "문항"]
    parts += ["### 난이도별", _table(level_header, [
        [m, d, *[summary[m]["by_difficulty"][d][k] for k, _ in METRICS[:3]],
         summary[m]["by_difficulty"][d]["n"]]
        for m in ("rag", "norag") for d in sorted(summary[m]["by_difficulty"])])]
    parts.append("## 대표 질문 나란히 보기")
    for i, p in enumerate(pick_examples(report), start=1):
        groups = (cases.get(p["id"]) or {}).get("answer_keywords") or []
        reference = " / ".join(" 또는 ".join(g) for g in groups) or "모른다고 답함"
        parts.append("\n".join([
            f"### {i}. [{p['type']}{', 어려움' if p['difficulty'] == 'hard' else ''}] "
            f"{p['question']} — {p['label']}",
            f"- 참고 정답: {reference}",
            f"- **RAG 없음** ({p['norag']['verdict']}): {truncate(p['norag']['answer'])}",
            f"- **RAG 사용** ({p['rag']['verdict']}): {truncate(p['rag']['answer'])}",
        ]))
    return "\n\n".join(parts)
