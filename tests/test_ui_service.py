from lyriclens.collect.cache import CollectCache
from lyriclens.config import load_settings
from lyriclens.domain.indexing import index_songs
from lyriclens.http import FetchError
from lyriclens.index.store import VectorStore
from lyriclens.ui.service import LyricLensService
from tests.fakes import FakeChatModel, FakeEmbeddings, FakeWikiClient, make_song

PAGES = [{"page_id": 1, "title": "星の街", "url": "u1", "text": "테스트 가수의 곡. " * 60}]


def _service(tmp_path, chat, wiki):
    store = VectorStore(tmp_path / "chroma", FakeEmbeddings())
    index_songs([make_song("ut_aa0001")], store, item_text_max_chars=6000, lyrics_chunk_lines=8)
    return LyricLensService(load_settings(), store, chat, wiki, CollectCache(tmp_path / "c.json"))


def test_ask_progress_order(tmp_path):
    """T-F2012-3 진행 단계 순서와 결과."""
    chat = FakeChatModel(["[]", "[]", "테스트 가수의 곡입니다 [근거 1]."])
    steps = []
    res = _service(tmp_path, chat, FakeWikiClient(PAGES)).ask(
        "ut_aa0001", "누구 노래?", [], on_step=lambda step, detail: steps.append(step)
    )
    assert steps == ["queries", "collect", "index", "answer"]
    assert [e.num for e in res.answer.cited] == [1]
    assert res.collect.chunk_count > 0


class BrokenWiki(FakeWikiClient):
    def find_page(self, title):
        raise FetchError("503")


def test_collect_failure_still_answers(tmp_path):
    """T-F2012-4 위키 수집이 실패해도 답변한다."""
    chat = FakeChatModel(["[]", "곡 정보로 답합니다 [근거 1]."])
    steps = []
    res = _service(tmp_path, chat, BrokenWiki(PAGES)).ask(
        "ut_aa0001", "누구 노래?", [], on_step=lambda step, detail: steps.append(step)
    )
    assert "collect_failed" in steps and steps[-1] == "answer"
    assert res.answer.text and res.collect is None
