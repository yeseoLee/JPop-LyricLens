from lyriclens.config import load_settings
from lyriclens.index.store import IndexDoc, VectorStore
from lyriclens.rag.graph import build_graph, graph_nodes
from tests.fakes import FakeChatModel, FakeEmbeddings


def _store(tmp_path):
    store = VectorStore(tmp_path, FakeEmbeddings())
    store.upsert(
        "song_meta",
        [
            IndexDoc(
                "ut_a",
                "제목: Lemon",
                {
                    "song_id": "ut_a",
                    "title": "Lemon",
                    "artist": "米津玄師",
                    "url": "u",
                    "source_type": "song_meta",
                },
            )
        ],
    )
    return store


def test_two_nodes(tmp_path):
    """T-F2007-1 그래프 노드는 retrieve, generate 두 개다."""
    graph = build_graph(_store(tmp_path), FakeChatModel(), load_settings())
    assert graph_nodes(graph) == {"retrieve", "generate"}


def test_graph_runs(tmp_path):
    """T-F2007-6 실행하면 근거와 답변이 상태에 채워진다."""
    chat = FakeChatModel(["Lemon은 米津玄師의 곡입니다 [근거 1]."])
    graph = build_graph(_store(tmp_path), chat, load_settings())
    out = graph.invoke({"song_id": "ut_a", "question": "누구 노래?", "history": []})
    assert out["evidence"][0].chunk_id == "ut_a"
    assert [e.num for e in out["answer"].cited] == [1]
