"""실제 브라우저로 앱을 조작하는 E2E 시나리오 (SPEC-012 §3.2).

    pytest -m e2e tests/e2e -s
"""

from __future__ import annotations

import re

import pytest

from tests.e2e.conftest import shot

pytestmark = pytest.mark.e2e

SIDEBAR = '[data-testid="stSidebar"]'
HANGUL = re.compile(r"[가-힣]")


def _no_internal_error(page) -> None:
    body = page.inner_text("body")
    assert "Traceback" not in body and "Exception" not in body


def _wait_idle(page) -> None:
    """Streamlit 재실행이 끝날 때까지 기다린다 (오른쪽 위 실행 표시가 사라짐)."""
    page.wait_for_timeout(500)
    page.locator('[data-testid="stStatusWidget"]').wait_for(state="hidden", timeout=180_000)


def _select_song(page, keyword: str) -> None:
    box = page.locator(f'{SIDEBAR} [data-testid="stSelectbox"]')
    box.click()
    page.keyboard.type(keyword)
    page.get_by_role("option", name=re.compile(re.escape(keyword))).first.click()
    _wait_idle(page)


def _tab(page, name: str) -> None:
    page.get_by_role("tab", name=re.compile(name)).click()
    page.wait_for_timeout(300)


def _ask(page, question: str) -> str:
    before = page.locator('[data-testid="stChatMessage"]').count()
    page.locator('[data-testid="stChatInputTextArea"]').fill(question)
    page.keyboard.press("Enter")
    page.locator('[data-testid="stChatMessage"]').nth(before + 1).wait_for()
    _wait_idle(page)
    return page.locator('[data-testid="stChatMessage"]').nth(before + 1).inner_text()


def test_e2e_1_home(page):
    """T-E2E-1 첫 화면: 제목·색인 건수·안내·탭 4개."""
    assert page.get_by_role("heading", name="JPop LyricLens").is_visible()
    sidebar = page.locator(SIDEBAR).inner_text()
    assert "곡 색인: 240곡" in sidebar
    assert "가사 저작권" in sidebar and "참고용" in sidebar
    assert page.get_by_role("tab").count() == 4
    _no_internal_error(page)
    shot(page, "01_home.png")


def test_e2e_2_chat_korean(page):
    """T-E2E-2 곡 선택 → 한국어 질문 → 답변과 근거 표시."""
    _select_song(page, "Lemon")
    _tab(page, "질문하기")
    answer = _ask(page, "이 곡은 어떤 드라마의 주제가인가요?")
    assert "언내추럴" in answer or "アンナチュラル" in answer or "Unnatural" in answer
    expander = page.locator('[data-testid="stExpander"]').filter(has_text="답변에 사용한 근거").last
    expander.click()
    text = expander.inner_text()
    assert "[근거" in text and expander.locator("a").count() >= 1
    _no_internal_error(page)
    shot(page, "02_chat_ko.png")


def test_e2e_3_chat_english(page):
    """T-E2E-3 영어 질문에는 영어로 답한다."""
    answer = _ask(page, "Who composed this song?")
    body = answer.split("답변에 사용한 근거")[0].replace("근거", "")
    assert len(HANGUL.findall(body)) <= 10, body
    assert re.search(r"[A-Za-z]{4,}", body)
    _no_internal_error(page)
    shot(page, "03_chat_en.png")


def test_e2e_4_condition(page):
    """T-E2E-4 조건 탐색 → 카드 → 이 곡으로 대화하기."""
    _tab(page, "조건으로 찾기")
    page.get_by_label(re.compile("어떤 곡을 찾나요")).fill("2020년 이후 애니메이션 주제가")
    page.get_by_role("button", name="찾기").first.click()
    buttons = page.get_by_role("button", name="이 곡으로 대화하기")
    buttons.or_(page.get_by_text("조건에 맞는 곡을 찾지 못했습니다")).first.wait_for()
    _wait_idle(page)
    assert buttons.count() >= 1
    shot(page, "04_condition.png")
    buttons.first.click()
    _wait_idle(page)
    assert page.get_by_text(re.compile("을\\(를\\) 선택했습니다")).is_visible()
    _no_internal_error(page)


def test_e2e_5_interpret(page):
    """T-E2E-5 구절 해석: 연 선택 → 번역·배경 표시."""
    _select_song(page, "Lemon")
    _tab(page, "구절 해석")
    page.get_by_label(re.compile("연 선택")).click()
    page.get_by_role("option").first.click()
    page.get_by_role("button", name="해석하기").click()
    page.get_by_text("참고용 번역").or_(page.get_by_text("찾지 못했습니다")).first.wait_for()
    _wait_idle(page)
    body = page.inner_text("body")
    assert "참고용 번역" in body and "곡 배경과의 연결" in body
    _no_internal_error(page)
    shot(page, "05_interpret.png")


def test_e2e_6_phrase_search(page):
    """T-E2E-6 한국어로 기억나는 가사 → 「Lemon」 1위."""
    _tab(page, "구절로 곡 찾기")
    page.get_by_label(re.compile("기억나는 가사")).fill("꿈이라면 얼마나 좋았을까")
    page.get_by_role("button", name="찾기").last.click()
    page.get_by_role("button", name="이 곡으로 대화하기").or_(
        page.get_by_text("일치하는 가사를 찾지 못했습니다")).first.wait_for()
    _wait_idle(page)
    panel = page.get_by_role("tabpanel").filter(has_text="기억나는 가사")
    cards = [ln for ln in panel.inner_text().splitlines() if " — " in ln and "UtaTen" in ln]
    assert cards and cards[0].startswith("Lemon"), cards[:3]
    _no_internal_error(page)
    shot(page, "06_phrase.png")


def test_e2e_7_switch_song(page):
    """T-E2E-7 다른 곡을 고르면 이전 곡의 대화가 보이지 않는다."""
    _select_song(page, "夜に駆ける")
    _tab(page, "질문하기")
    assert "이 곡은 어떤 드라마의 주제가인가요?" not in page.inner_text("body")
    _no_internal_error(page)
    shot(page, "07_switch.png")
