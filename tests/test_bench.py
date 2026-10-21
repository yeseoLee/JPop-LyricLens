import json
from pathlib import Path

import pytest

from lyriclens.bench.cases import (
    MIN_COUNTS,
    load_lyric_refs,
    load_qa_cases,
    load_search_cases,
    resolve_cases,
    validate_cases,
)
from lyriclens.bench.metrics import hit_at_k, mrr_at_k, ndcg_at_k, recall_at_k
from lyriclens.bench.runner import run_search, summary_markdown
from lyriclens.bench.scoring import keyword_correct, parse_judgement

ROOT = Path(__file__).resolve().parents[1]
SONGS = ROOT / "data" / "songs.jsonl"


def test_metrics_hand_computed():
    """T-BENCH-1 지표가 손 계산과 일치한다."""
    ranked = ["a", "x", "b", "y"]
    rel = {"a", "b", "c"}
    assert hit_at_k(ranked, rel, 1) == 1 and hit_at_k(["x"], rel, 1) == 0
    assert recall_at_k(ranked, rel, 3) == pytest.approx(2 / 3)
    assert recall_at_k(ranked, {"a"}, 10) == 1.0
    assert mrr_at_k(["x", "y", "b"], rel, 10) == pytest.approx(1 / 3)
    assert mrr_at_k(["x"] * 11 + ["a"], rel, 10) == 0
    # DCG = 1/log2(2) + 1/log2(4) = 1.5, IDCG(3개 관련) = 1 + 1/log2(3) + 1/log2(4)
    assert ndcg_at_k(ranked, rel, 10) == pytest.approx(1.5 / (1 + 1 / 1.5849625 + 0.5), rel=1e-4)


def test_case_files_valid():
    """T-BENCH-2 케이스 파일 스키마·id 유일·범주별 최소 개수·split."""
    search = load_search_cases(ROOT / "bench/search_cases.yaml")
    refs = load_lyric_refs(ROOT / "bench/lyric_refs.yaml")
    qa = load_qa_cases(ROOT / "bench/qa_cases.yaml")
    assert validate_cases(search, refs, qa) == []
    cats = {c["category"] for c in search} | {r["category"] for r in refs}
    assert set(MIN_COUNTS) <= cats
    assert len(qa) >= 60 and {"dev", "test"} <= {c["split"] for c in search + refs + qa}


def test_validation_catches_errors():
    """T-BENCH-2 잘못된 케이스를 잡아낸다."""
    bad = [
        {"id": "x", "category": "title_ja", "lang": "jp", "query": "a", "split": "dev"},
        {
            "id": "x",
            "category": "title_ja",
            "lang": "ja",
            "query": "b",
            "split": "dev",
            "relevant": [],
        },
    ]
    errors = validate_cases(bad, [], [], min_counts={})
    assert any("lang" in e for e in errors) and any("중복" in e for e in errors)
    assert any("relevant" in e for e in errors)


@pytest.mark.skipif(not SONGS.exists(), reason="data/songs.jsonl 없음")
def test_relevant_resolves_to_song_ids():
    """T-BENCH-3 정답 제목·아티스트가 실제 song_id 로 풀린다."""
    songs = [json.loads(line) for line in SONGS.open(encoding="utf-8")]
    search = load_search_cases(ROOT / "bench/search_cases.yaml")
    resolved, missing = resolve_cases(search, songs)
    assert missing == []
    assert all(c["relevant_ids"] for c in resolved)
    artist = next(c for c in resolved if c.get("relevant_artist") == "YOASOBI")
    assert len(artist["relevant_ids"]) == 6


@pytest.mark.skipif(not SONGS.exists(), reason="data/songs.jsonl 없음")
def test_lyric_refs_valid_and_not_committed():
    """T-BENCH-4 가사 참조가 실제 줄을 가리키고, 저장소 파일에 가사 원문이 없다."""
    from lyriclens.bench.cases import materialize_lyric_queries

    songs = [json.loads(line) for line in SONGS.open(encoding="utf-8")]
    refs = load_lyric_refs(ROOT / "bench/lyric_refs.yaml")
    ja = [r for r in refs if r["lang"] == "ja"]
    cases, missing = materialize_lyric_queries(ja, songs, translations={})
    assert missing == [] and all(c["query"] for c in cases)
    committed = "".join(
        (ROOT / "bench" / f).read_text(encoding="utf-8")
        for f in ("search_cases.yaml", "lyric_refs.yaml")
    )
    assert not [c["query"] for c in cases if len(c["query"]) >= 6 and c["query"] in committed]


def test_keyword_scoring():
    """T-BENCH-5 대체 표기·전각/반각·대소문자를 처리한다."""
    groups = [["米津玄師", "Kenshi Yonezu"], ["2018"]]
    assert keyword_correct("작곡은 KENSHI  YONEZU, 발매는 ２０１８년", groups)
    assert not keyword_correct("작곡은 요네즈", groups)
    assert keyword_correct("SPY X FAMILY", [["spy×family", "spy x family"]])


def test_parse_judgement():
    """T-BENCH-6 LLM 판정 JSON 파싱, 실패 시 unknown."""
    assert parse_judgement('```json\n{"verdict": "correct"}\n```') == "correct"
    assert parse_judgement('{"verdict": "ABSTAIN", "reason": "모름"}') == "abstain"
    assert parse_judgement("판정 불가") == "unknown"
    assert parse_judgement('{"verdict": "maybe"}') == "unknown"


def test_run_search_summary():
    """T-BENCH-7 대역 시스템으로 범주·언어·split별 요약을 낸다."""
    cases = [
        {
            "id": "1",
            "category": "title_ja",
            "lang": "ja",
            "split": "dev",
            "query": "a",
            "relevant_ids": ["s1"],
        },
        {
            "id": "2",
            "category": "title_ko",
            "lang": "ko",
            "split": "test",
            "query": "b",
            "relevant_ids": ["s2"],
        },
    ]
    systems = {"perfect": lambda q: ["s1"] if q == "a" else ["s2"], "none": lambda q: []}
    report = run_search(cases, systems)
    assert report["summary"]["perfect"]["all"]["hit@1"] == 1.0
    assert report["summary"]["none"]["all"]["mrr@10"] == 0.0
    assert report["summary"]["perfect"]["by_category"]["title_ko"]["n"] == 1
    assert set(report["summary"]["perfect"]["by_split"]) == {"dev", "test"}
    assert "| perfect |" in summary_markdown(report)


def test_typo_queries_are_not_exact():
    """T-BENCH-8 오탈자 질의는 정답 표기와 정확히 같지 않다."""
    for c in load_search_cases(ROOT / "bench/search_cases.yaml"):
        if c["category"] != "typo":
            continue
        names = {r["title"] for r in c.get("relevant") or []} | {c.get("relevant_artist")}
        assert c["query"] not in names, c["id"]


def test_run_qa_summary():
    """T-BENCH-9 QA 실행기가 모드별·유형별 지표를 낸다."""
    from lyriclens.bench.qa import run_qa
    from tests.fakes import FakeChatModel

    cases = [
        {
            "id": "q1",
            "type": "credit",
            "lang": "ko",
            "split": "dev",
            "question": "작곡가?",
            "song_id": "s1",
            "answer_keywords": [["米津玄師", "요네즈"]],
        },
        {
            "id": "q2",
            "type": "unanswerable",
            "lang": "ko",
            "split": "test",
            "question": "마이크 모델?",
            "song_id": "s1",
        },
        {
            "id": "q3",
            "type": "release",
            "lang": "en",
            "split": "dev",
            "question": "year?",
            "song_id": "s1",
            "answer_keywords": [["2018"]],
        },
    ]
    answers = {
        "q1": "요네즈 켄시입니다 [근거 1]",
        "q2": "제공된 문서에서 확인되지 않습니다.",
        "q3": "It was released in 2017.",
    }
    judge = FakeChatModel(
        ['{"verdict": "correct"}', '{"verdict": "abstain"}', '{"verdict": "incorrect"}']
    )
    report = run_qa(cases, {"rag": lambda c: answers[c["id"]]}, judge)
    s = report["summary"]["rag"]["all"]
    assert s["kw_acc"] == 0.5 and s["llm_acc"] == 0.5
    assert s["abstain_rate"] == 1.0 and s["wrong_rate"] == 0.5
    assert s["citation_rate"] == pytest.approx(1 / 3, abs=1e-3)
    assert s["agreement"] == 1.0
    assert report["summary"]["rag"]["by_type"]["credit"]["kw_acc"] == 1.0


def test_judge_prompt_and_norag_prompt():
    """T-BENCH-10 판정 프롬프트와 norag 프롬프트 내용."""
    from lyriclens.bench.qa import judge_answer, norag_answer
    from tests.fakes import FakeChatModel

    judge = FakeChatModel(['{"verdict": "abstain"}'])
    case = {"type": "unanswerable", "question": "마이크 모델?", "lang": "ko"}
    assert judge_answer(case, "모르겠습니다", judge) == "abstain"
    human = judge.calls[0][-1].content
    assert "마이크 모델?" in human and "모르겠습니다" in human and "모른다고" in human

    chat = FakeChatModel(["답"])
    norag_answer({"question": "작곡가?", "song_title": "Lemon", "song_artist": "米津玄師"}, chat)
    system = chat.calls[0][0].content
    assert "모르" in system and "Lemon" in chat.calls[0][-1].content
