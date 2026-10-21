"""답변 품질 벤치마크 실행 — RAG 있음/없음, 키워드·LLM 판정 (SPEC-015 §4)."""

from __future__ import annotations

import time
from collections.abc import Callable

from langchain_core.messages import HumanMessage, SystemMessage

from lyriclens.bench.scoring import keyword_correct, parse_judgement
from lyriclens.rag import prompts
from lyriclens.rag.citations import cited_numbers

UNANSWERABLE_REFERENCE = "모른다고 답함 (근거 문서로 답할 수 없는 질문)"


def norag_answer(case: dict, chat) -> str:
    human = prompts.NORAG_HUMAN.format(title=case["song_title"], artist=case["song_artist"],
                                       question=case["question"])
    return chat.invoke([SystemMessage(prompts.NORAG_SYSTEM), HumanMessage(human)]).content


def judge_answer(case: dict, answer: str, judge_chat) -> str:
    if case["type"] == "unanswerable":
        reference = UNANSWERABLE_REFERENCE
    else:
        reference = " / ".join(" 또는 ".join(g) for g in case["answer_keywords"])
    human = prompts.JUDGE_HUMAN.format(question=case["question"], reference=reference,
                                       answer=answer)
    return parse_judgement(
        judge_chat.invoke([SystemMessage(prompts.JUDGE_SYSTEM), HumanMessage(human)]).content
    )


def _rate(rows: list[dict], pred) -> float | None:
    """해당 문항이 없으면 None (표에는 '-')."""
    return round(sum(1 for r in rows if pred(r)) / len(rows), 4) if rows else None


def _aggregate(rows: list[dict]) -> dict:
    answerable = [r for r in rows if r["type"] != "unanswerable"]
    unanswerable = [r for r in rows if r["type"] == "unanswerable"]
    return {
        "n": len(rows),
        "kw_acc": _rate(answerable, lambda r: r["kw_correct"]),
        "llm_acc": _rate(answerable, lambda r: r["verdict"] == "correct"),
        "wrong_rate": _rate(answerable, lambda r: r["verdict"] == "incorrect"),
        "agreement": _rate(answerable, lambda r: r["kw_correct"] == (r["verdict"] == "correct")),
        "abstain_rate": _rate(unanswerable, lambda r: r["verdict"] == "abstain"),
        "citation_rate": _rate(rows, lambda r: r["cited"]),
        "sec/question": round(sum(r["sec"] for r in rows) / len(rows), 2) if rows else 0.0,
    }


def _group(rows: list[dict], key: str) -> dict:
    groups: dict[str, list[dict]] = {}
    for r in rows:
        groups.setdefault(r[key], []).append(r)
    return {k: _aggregate(v) for k, v in sorted(groups.items())}


def run_qa(cases: list[dict], modes: dict[str, Callable[[dict], str]], judge_chat,
           on_case=lambda mode, case, row: None) -> dict:
    """modes: 이름 → (케이스 → 답변 문자열)."""
    report = {"rows": {}, "summary": {}}
    for mode, answer_fn in modes.items():
        rows = []
        for case in cases:
            t = time.time()
            try:
                answer, error = answer_fn(case), None
            except Exception as exc:
                answer, error = "", repr(exc)
            sec = time.time() - t
            groups = case.get("answer_keywords") or []
            row = {"id": case["id"], "type": case["type"], "lang": case["lang"],
                   "split": case["split"], "question": case["question"], "answer": answer,
                   "difficulty": "hard" if case.get("hard") else "normal",
                   "error": error, "sec": sec,
                   "kw_correct": bool(groups) and keyword_correct(answer, groups),
                   "verdict": judge_answer(case, answer, judge_chat) if answer else "unknown",
                   "cited": bool(cited_numbers(answer))}
            rows.append(row)
            on_case(mode, case, row)
        report["rows"][mode] = rows
        report["summary"][mode] = {"all": _aggregate(rows), "by_type": _group(rows, "type"),
                                   "by_lang": _group(rows, "lang"),
                                   "by_split": _group(rows, "split"),
                                   "by_difficulty": _group(rows, "difficulty")}
    return report


QA_METRICS = ["kw_acc", "llm_acc", "wrong_rate", "agreement", "abstain_rate", "citation_rate",
              "sec/question"]


def qa_markdown(report: dict) -> str:
    def table(header, lines):
        out = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
        cell = lambda c: "-" if c is None else str(c)  # noqa: E731
        return "\n".join(out + ["| " + " | ".join(cell(c) for c in ln) + " |" for ln in lines])

    summary = report["summary"]
    parts = ["### 전체", table(["모드", *QA_METRICS, "n"], [
        [m, *[s["all"][k] for k in QA_METRICS], s["all"]["n"]] for m, s in summary.items()])]
    types = sorted({t for s in summary.values() for t in s["by_type"]})
    parts += ["### 유형별 LLM 정답률 (unanswerable 은 모름 인정률)", table(["모드", *types], [
        [m, *[(s["by_type"][t]["abstain_rate"] if t == "unanswerable"
               else s["by_type"][t]["llm_acc"]) if t in s["by_type"] else "-" for t in types]]
        for m, s in summary.items()])]
    levels = sorted({d for s in summary.values() for d in s.get("by_difficulty", {})})
    parts += ["### 난이도별", table(["모드", "난이도", *QA_METRICS[:-1], "n"], [
        [m, d, *[s["by_difficulty"][d][k] for k in QA_METRICS[:-1]], s["by_difficulty"][d]["n"]]
        for m, s in summary.items() for d in levels if d in s.get("by_difficulty", {})])]
    return "\n\n".join(parts)
