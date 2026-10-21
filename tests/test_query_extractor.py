from lyriclens.collect.models import SongInfo
from lyriclens.collect.query_extractor import extract_queries
from tests.fakes import FakeChatModel

SONG = SongInfo("ut_1", "Lemon", "米津玄師", "요네즈 켄시", "ドラマ「アンナチュラル」主題歌")


def test_base_queries_first():
    """T-F2003-1 곡 제목·아티스트가 항상 앞에 온다."""
    chat = FakeChatModel(['["드라마 언내추럴"]'])
    assert extract_queries(SONG, "주제가?", chat, 4) == ["Lemon", "요네즈 켄시", "드라마 언내추럴"]
    system = chat.calls[0][0].content
    assert "J-POP" in system and "JSON" in system


def test_code_block_parsed():
    """T-F2003-2 코드블록으로 감싼 JSON도 파싱한다."""
    chat = FakeChatModel(['```json\n["언내추럴", "Lemon"]\n```'])
    assert extract_queries(SONG, "q", chat, 4) == ["Lemon", "요네즈 켄시", "언내추럴"]


def test_unparseable_falls_back():
    """T-F2003-3 두 번 모두 파싱 실패하면 기본 검색어만 쓴다."""
    chat = FakeChatModel(["모르겠어요", "여전히 모름"])
    assert extract_queries(SONG, "q", chat, 4) == ["Lemon", "요네즈 켄시"]
    assert len(chat.calls) == 2


def test_query_limit():
    """T-F2003-4 LLM 검색어는 max_queries 개까지만."""
    chat = FakeChatModel(['["a","b","c","d","e","f","g","h","i","j"]'])
    assert len(extract_queries(SONG, "q", chat, 4)) == 2 + 4
