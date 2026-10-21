import time

from lyriclens.collect.cache import CollectCache
from lyriclens.collect.collector import collect_documents
from lyriclens.collect.models import SongInfo
from lyriclens.collect.prefetch import prefetch_primary
from lyriclens.config import load_settings
from lyriclens.index.store import VectorStore
from lyriclens.rag.evidence import Evidence
from lyriclens.rag.generate import generate_answer, generate_answer_stream
from tests.fakes import FakeChatModel, FakeEmbeddings, FakeWikiClient

SONG = SongInfo("ut_1", "Lemon", "米津玄師", "요네즈 켄시")
LONG = "가" * 300
PAGES = [
    {"page_id": 1, "title": "Lemon", "url": "u1", "text": LONG},
    {"page_id": 2, "title": "요네즈 켄시", "url": "u2", "text": LONG},
]


class SlowWiki(FakeWikiClient):
    def find_page(self, title):
        time.sleep(0.15)
        return super().find_page(title)


def test_extract_and_primary_run_concurrently(tmp_path):
    """T-NF2001-1 검색어 추출과 1차 문서 찾기를 동시에 실행한다."""
    chat = FakeChatModel(["[]"])
    chat.delay = 0.3
    t = time.time()
    collect_documents(
        SONG, "q", chat, SlowWiki(PAGES), CollectCache(tmp_path / "c.json"), load_settings()
    )
    assert time.time() - t < 0.5  # 직렬이면 0.3 + 0.15*2 = 0.6초 이상


def test_prefetch_marks_primary_done(tmp_path):
    """T-NF2001-2, T-NF2001-3 미리 수집한 곡은 질문 때 1차 문서를 찾지 않는다."""
    store = VectorStore(tmp_path / "chroma", FakeEmbeddings())
    cache = CollectCache(tmp_path / "c.json")
    wiki = FakeWikiClient(PAGES)
    n = prefetch_primary([SONG], wiki, cache, store, load_settings())
    assert n == 1 and cache.primary_done("ut_1") and store.count("wiki_docs") >= 2

    again = FakeWikiClient(PAGES)
    assert (
        prefetch_primary([SONG], again, CollectCache(tmp_path / "c.json"), store, load_settings())
        == 0
    )
    assert again.calls == []

    asked = FakeWikiClient(PAGES)
    collect_documents(
        SONG,
        "새 질문",
        FakeChatModel(['["드라마"]', "[]"]),
        asked,
        CollectCache(tmp_path / "c.json"),
        load_settings(),
    )
    assert asked.count("find_page") == 0 and asked.count("fetch") == 0


EV = [Evidence(1, "ut_1", "song_meta", "Lemon — 米津玄師", "u", "제목: Lemon", {})]


def test_stream_matches_non_stream():
    """T-NF2001-4 스트리밍 조각을 합치면 최종 답변과 같고 인용도 같다."""
    text = "드라마 언내추럴의 주제가입니다 [근거 1]."
    chunks, final = [], None
    for item in generate_answer_stream("주제가?", EV, FakeChatModel([text]), load_settings()):
        if isinstance(item, str):
            chunks.append(item)
        else:
            final = item
    assert "".join(chunks) == final.text == text
    plain = generate_answer("주제가?", EV, FakeChatModel([text]), load_settings())
    assert [e.num for e in final.cited] == [e.num for e in plain.cited] == [1]


def test_stream_without_evidence_no_llm():
    """T-NF2001-4 근거가 없으면 LLM을 부르지 않는다."""
    chat = FakeChatModel(["x"])
    items = list(generate_answer_stream("주제가?", [], chat, load_settings()))
    assert chat.calls == [] and items[-1].no_citation
