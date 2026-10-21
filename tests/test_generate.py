from lyriclens.config import load_settings
from lyriclens.rag import prompts
from lyriclens.rag.evidence import Evidence
from lyriclens.rag.generate import format_evidence, generate_answer
from tests.fakes import FakeChatModel

EV = [
    Evidence(1, "ut_a", "song_meta", "Lemon — 米津玄師", "u1", "제목: Lemon", {}),
    Evidence(2, "ut_a:7:0", "wikipedia", "언내추럴", "u2", "드라마 언내추럴의 주제가", {}),
]


def test_evidence_block_headers():
    """T-F2007-2 근거 블록마다 [근거 N] (유형) 제목 머리말이 있다."""
    block = format_evidence(EV)
    assert "[근거 1] (곡 정보) Lemon — 米津玄師" in block
    assert "[근거 2] (위키백과) 언내추럴" in block


def test_no_evidence_no_llm_call():
    """T-F2007-3 근거가 없으면 LLM을 부르지 않고 확인 불가로 답한다."""
    chat = FakeChatModel(["안 불려야 함"])
    ans = generate_answer("주제가가 뭐야?", [], chat, load_settings())
    assert chat.calls == [] and ans.no_citation
    assert ans.text == prompts.NOT_FOUND["ko"]
    assert generate_answer("What?", [], chat, load_settings()).text == prompts.NOT_FOUND["en"]


def test_system_prompt_rules():
    """T-F2007-4 시스템 프롬프트에 핵심 규칙이 있다."""
    chat = FakeChatModel(["드라마 언내추럴 주제가입니다 [근거 2]."])
    ans = generate_answer("주제가가 뭐야?", EV, chat, load_settings(), history=[("user", "안녕")])
    system = chat.calls[0][0].content
    for rule in ["근거]에 있는 내용만", "확인되지 않습니다", "[근거 N]", "같은 언어", "최대 4줄"]:
        assert rule in system
    human = chat.calls[0][-1].content
    assert "[근거 2] (위키백과) 언내추럴" in human and "안녕" in human
    assert [e.num for e in ans.cited] == [2] and not ans.no_citation


def test_answer_without_markers_flags():
    """T-F2008-3 답변에 인용이 없으면 no_citation."""
    ans = generate_answer("q", EV, FakeChatModel(["그냥 답"]), load_settings())
    assert ans.no_citation and ans.cited == []
