"""통합 곡 검색 — 어휘·LLM 해석·곡 정보 벡터·가사 벡터 채널을 가중 RRF로 결합 (SPEC-016)."""

from __future__ import annotations

from dataclasses import dataclass, field

from langchain_core.messages import HumanMessage, SystemMessage

from lyriclens.jsonparse import invoke_json
from lyriclens.rag import prompts
from lyriclens.rag.retrieve import SONG_LYRICS, SONG_META
from lyriclens.services.search_catalog import Catalog

EXACT = 1.0
VECTOR_K = 30


@dataclass
class SearchHit:
    song_id: str
    title: str
    artist: str
    score: float
    channels: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)


def rrf_fuse(rankings: dict[str, list[str]], weights: dict[str, float], k: int = 60,
             pinned: list[str] | None = None) -> list[str]:
    scores: dict[str, float] = {}
    for channel, ranked in rankings.items():
        for rank, sid in enumerate(ranked, start=1):
            scores[sid] = scores.get(sid, 0.0) + weights.get(channel, 1.0) / (k + rank)
    order = sorted(scores, key=lambda sid: -scores[sid])
    pinned = [p for p in (pinned or []) if p in scores]
    return pinned + [sid for sid in order if sid not in pinned]


def _per_song(hits) -> dict[str, float]:
    best: dict[str, float] = {}
    for doc, score in hits:
        sid = doc.metadata["song_id"]
        best[sid] = max(best.get(sid, -1.0), score)
    return dict(sorted(best.items(), key=lambda kv: -kv[1]))


def route_kind(lexical_best: float, lyrics_top: float, meta_top: float, margin: float) -> str:
    """LLM 없이 질의 유형을 정한다 (SPEC-016 §2.4.1)."""
    if lexical_best >= 0.85:
        return "name"
    if lyrics_top >= meta_top + margin:
        return "lyrics"
    return "description"


def _llm_guess(query: str, chat) -> dict:
    data = invoke_json(chat, [SystemMessage(prompts.UNIFIED_QUERY_SYSTEM), HumanMessage(query)],
                       dict, retries=0)
    return data or {}


def unified_search(query: str, catalog: Catalog, store, chat, settings) -> list[SearchHit]:
    cfg = settings.search
    threshold = cfg.get("lexical_threshold", 0.75)
    rankings: dict[str, list[str]] = {}
    reasons: dict[str, list[str]] = {}
    channels_of: dict[str, list[str]] = {}

    def note(channel: str, sid: str, reason: str | None = None) -> None:
        channels_of.setdefault(sid, [])
        if channel not in channels_of[sid]:
            channels_of[sid].append(channel)
        if reason:
            reasons.setdefault(sid, []).append(reason)

    lexical = catalog.match(query, threshold)
    rankings["lexical"] = [m.song_id for m in lexical]
    pinned = [m.song_id for m in lexical if m.score >= EXACT]
    for m in lexical:
        note("lexical", m.song_id, m.reasons[0])

    queries = [query]
    guess: dict = {}
    if cfg.get("use_llm", True):
        guess = _llm_guess(query, chat)
        ja = guess.get("ja_query")
        if isinstance(ja, str) and ja.strip() and ja.strip() != query:
            queries.append(ja.strip())
        guessed: dict[str, float] = {}
        for kind in ("title_guess", "artist_guess"):
            for name in guess.get(kind) or []:
                if not isinstance(name, str):
                    continue
                for m in catalog.match(name, 0.85):  # 카탈로그에 있는 곡만
                    if m.score > guessed.get(m.song_id, 0):
                        guessed[m.song_id] = m.score
                        note("llm_guess", m.song_id, f"질의 해석: {name}")
        rankings["llm_guess"] = sorted(guessed, key=lambda sid: -guessed[sid])

    meta, lyrics = [], []
    for q in queries:
        meta += store.search(SONG_META, q, VECTOR_K)
        lyrics += store.search(SONG_LYRICS, q, VECTOR_K)
    meta_scores, lyrics_scores = _per_song(meta), _per_song(lyrics)
    depth = cfg.get("vector_depth", 10)
    rankings["meta_vector"] = list(meta_scores)[:depth]
    rankings["lyrics_vector"] = list(lyrics_scores)[:depth]

    # 질의 유형은 규칙으로 정한다. LLM 의 kind 는 일본어 가사를 제목·설명으로 잘못 보는
    # 일이 잦아 쓰지 않는다 (dev 측정, SPEC-016 §2.4.1). LLM 은 곡·아티스트 추정에만 쓴다.
    kind = route_kind(max((m.score for m in lexical), default=0.0),
                      next(iter(lyrics_scores.values()), 0.0),
                      next(iter(meta_scores.values()), 0.0),
                      cfg.get("lyrics_margin", 0.05))
    weights = (cfg.get("route_weights") or {}).get(kind) or cfg.get("weights", {})
    for sid in rankings["meta_vector"][:3]:
        note("meta_vector", sid, "곡 정보 의미 검색")
    for sid in rankings["lyrics_vector"][:3]:
        note("lyrics_vector", sid, "가사 검색")
    for channel in ("meta_vector", "lyrics_vector"):
        for sid in rankings[channel]:
            note(channel, sid)

    order = rrf_fuse(rankings, weights, cfg.get("rrf_k", 60), pinned)
    hits = []
    for sid in order[: cfg.get("top_k", 10)]:
        meta_info = catalog.metas.get(sid, {})
        hits.append(SearchHit(sid, meta_info.get("title", ""), meta_info.get("artist", ""),
                              0.0, channels_of.get(sid, []), reasons.get(sid, [])))
    return hits
