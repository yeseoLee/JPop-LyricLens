"""벤치마크에서 비교할 곡 찾기 시스템 (SPEC-015 §3.6). 질의 → song_id 순위 목록."""

from __future__ import annotations

from dataclasses import replace

from lyriclens.rag.retrieve import SONG_LYRICS, SONG_META
from lyriclens.services.condition_search import search_by_condition
from lyriclens.services.phrase_search import search_phrase
from lyriclens.services.unified_search import unified_search

TOP_K = 10


def _per_song(hits) -> list[str]:
    best: dict[str, float] = {}
    for doc, score in hits:
        sid = doc.metadata["song_id"]
        best[sid] = max(best.get(sid, -1.0), score)
    return [sid for sid, _ in sorted(best.items(), key=lambda kv: -kv[1])][:TOP_K]


def build_search_systems(store, aux_chat, settings, names: list[str] | None = None,
                         catalog=None) -> dict:
    systems = {
        "meta_vector": lambda q: [d.id for d, _ in store.search(SONG_META, q, TOP_K)],
        "lyrics_vector": lambda q: _per_song(store.search(SONG_LYRICS, q, TOP_K * 3)),
        "phrase_search": lambda q: [h.song_id for h in search_phrase(q, store, aux_chat,
                                                                     settings)][:TOP_K],
        "condition_search": lambda q: [m.song_id for m in search_by_condition(
            q, store, aux_chat, settings).matches][:TOP_K],
    }
    if catalog is not None:  # 통합 검색 (SPEC-016)
        no_llm = replace(settings, search={**settings.search, "use_llm": False})
        systems["unified"] = lambda q: [h.song_id for h in unified_search(
            q, catalog, store, aux_chat, settings)][:TOP_K]
        systems["unified_nollm"] = lambda q: [h.song_id for h in unified_search(
            q, catalog, store, aux_chat, no_llm)][:TOP_K]
    return {k: v for k, v in systems.items() if names is None or k in names}
