from lyriclens.collect.candidate_selector import select_candidates
from lyriclens.collect.models import SongInfo
from lyriclens.collect.wikipedia import WikiCandidate
from tests.fakes import FakeChatModel

SONG = SongInfo("ut_1", "Lemon", "米津玄師", "요네즈 켄시")
CANDS = [WikiCandidate(1, "언내추럴", "드라마"), WikiCandidate(2, "레몬", "과일")]


def test_select_ignores_unknown_ids():
    """T-F2004-8 후보에 없는 ID는 무시한다."""
    chat = FakeChatModel(["[1, 99]"])
    assert select_candidates(SONG, "q", CANDS, chat) == {1}
    assert "언내추럴" in chat.calls[0][-1].content


def test_select_parse_failure_empty():
    """T-F2004-8 파싱 실패가 반복되면 빈 집합."""
    assert select_candidates(SONG, "q", CANDS, FakeChatModel(["x", "y"])) == set()


def test_no_candidates_no_call():
    """T-F2004-1 후보가 없으면 LLM을 부르지 않는다."""
    chat = FakeChatModel(["[1]"])
    assert select_candidates(SONG, "q", [], chat) == set()
    assert chat.calls == []
