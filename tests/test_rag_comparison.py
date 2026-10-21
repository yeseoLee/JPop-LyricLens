from lyriclens.bench.comparison import comparison_markdown, pick_examples, truncate

TYPES = ["credit", "release", "tieup", "background", "meaning", "unanswerable"]


def _row(i, t, verdict, kw, answer="답", hard=False):
    return {"id": f"Q-{t}-{i:02d}", "type": t, "lang": "ko", "split": "dev",
            "question": f"{t} 질문 {i}", "answer": answer, "verdict": verdict, "kw_correct": kw,
            "cited": "[근거" in answer, "difficulty": "hard" if hard else "normal", "sec": 1.0}


def _report():
    rag, norag = [], []
    for t in TYPES:
        for i in range(1, 4):
            if t == "unanswerable":
                rag.append(_row(i, t, "abstain", False, "확인되지 않습니다 [근거 1]"))
                norag.append(_row(i, t, "incorrect" if i == 1 else "abstain", False, "지어낸 답"))
            else:
                rag.append(_row(i, t, "correct", True, "정답 [근거 1]", hard=i == 1))
                ok = i != 1
                norag.append(_row(i, t, "correct" if ok else "incorrect", ok, "답", hard=i == 1))
    # 채점이 엇갈린 문항 (제외되어야 함)
    rag[0]["kw_correct"] = False
    from lyriclens.bench.qa import _aggregate, _group

    def summary(rows):
        return {"all": _aggregate(rows), "by_difficulty": _group(rows, "difficulty")}

    cases = {r["id"]: {"answer_keywords": [["정답"]]} for r in rag}
    return {"rows": {"rag": rag, "norag": norag},
            "summary": {"rag": summary(rag), "norag": summary(norag)}}, cases


def test_report_tables():
    """T-F2015-1 요약 표와 난이도별 표."""
    report, cases = _report()
    md = comparison_markdown(report, cases)
    assert "| rag |" in md and "| norag |" in md
    assert "hard" in md and "모름 인정률" in md


def test_pick_examples():
    """T-F2015-2 유형별 최소 1개·총 8개 이상, meaning 제외, 엇갈린 채점 제외, 우선순위."""
    report, _ = _report()
    picked = pick_examples(report, minimum=8)
    types = {p["type"] for p in picked}
    assert "meaning" not in types
    assert {"credit", "release", "tieup", "background", "unanswerable"} <= types
    assert len(picked) >= 8
    assert "Q-credit-01" not in {p["id"] for p in picked}  # rag 채점이 엇갈린 문항
    first_of = {}
    for p in picked:
        first_of.setdefault(p["type"], p)
    assert first_of["release"]["id"] == "Q-release-01"  # RAG만 맞힌 문항이 먼저
    assert first_of["unanswerable"]["id"] == "Q-unanswerable-01"  # RAG만 모름 인정


def test_truncate():
    """T-F2015-3 300자로 자르고 … 표시."""
    assert truncate("가" * 400, 300) == "가" * 300 + "…"
    assert truncate("짧음", 300) == "짧음"
