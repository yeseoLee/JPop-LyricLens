"""LangGraph RAG 파이프라인 — retrieve → generate 두 노드 (SPEC-007 §3.5, F2007)."""

from __future__ import annotations

from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from lyriclens.rag.evidence import Evidence
from lyriclens.rag.generate import Answer, generate_answer
from lyriclens.rag.retrieve import retrieve


class RagState(TypedDict, total=False):
    song_id: str
    question: str
    history: list[tuple[str, str]]
    evidence: list[Evidence]
    answer: Answer


def build_graph(store, chat, settings):
    def retrieve_node(state: RagState) -> dict:
        return {"evidence": retrieve(store, state["song_id"], state["question"], settings)}

    def generate_node(state: RagState) -> dict:
        return {"answer": generate_answer(state["question"], state["evidence"], chat, settings,
                                          state.get("history", []))}

    graph = StateGraph(RagState)
    graph.add_node("retrieve", retrieve_node)
    graph.add_node("generate", generate_node)
    graph.add_edge(START, "retrieve")
    graph.add_edge("retrieve", "generate")
    graph.add_edge("generate", END)
    return graph.compile()


def graph_nodes(graph) -> set[str]:
    return {n for n in graph.get_graph().nodes if not n.startswith("__")}
