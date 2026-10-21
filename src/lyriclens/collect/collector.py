"""외부 문서 수집 흐름 — 검색어 추출 → 1차 문서 → 후보 선별 → 본문 수집 (SPEC-004 §3.5)."""

from __future__ import annotations

from lyriclens.collect.cache import CollectCache
from lyriclens.collect.candidate_selector import select_candidates
from lyriclens.collect.models import CollectedDoc, CollectResult, SongInfo, WikiCandidate
from lyriclens.collect.query_extractor import extract_queries


def _is_song_page(title: str, song_title: str) -> bool:
    return title == song_title or title.startswith(f"{song_title} (")


def _primary_candidates(song: SongInfo, wiki, limit: int) -> list[tuple[WikiCandidate, str]]:
    found: list[tuple[WikiCandidate, str]] = []
    song_page = wiki.find_page(song.title)
    if not (song_page and _is_song_page(song_page.title, song.title)):
        song_page = next(
            (c for c in wiki.search(song.title, limit) if _is_song_page(c.title, song.title)),
            None,
        )
    if song_page:
        found.append((song_page, song.title))
    artist_page = wiki.find_page(song.artist_query)
    if artist_page and all(artist_page.page_id != c.page_id for c, _ in found):
        found.append((artist_page, song.artist_query))
    return found


def collect_documents(song: SongInfo, question: str, chat, wiki, cache: CollectCache,
                      settings) -> CollectResult:
    cfg = settings.collect
    result = CollectResult(queries=extract_queries(song, question, chat, cfg["max_queries"]))
    result.cached_queries = [q for q in result.queries if cache.has_query(song.song_id, q)]
    pending = [q for q in result.queries if q not in result.cached_queries]
    if not pending:
        return result

    known = cache.page_ids(song.song_id)
    seen: set[int] = set(known)

    for cand, query in _primary_candidates(song, wiki, cfg["candidates_per_query"]):
        if cand.page_id not in seen:
            seen.add(cand.page_id)
            result.indexed.append(CollectedDoc(wiki.fetch(cand.page_id), query, True))

    base = {song.title, song.artist_query}
    candidates: list[tuple[WikiCandidate, str]] = []
    for query in pending:
        if query in base:
            continue
        for cand in wiki.search(query, cfg["candidates_per_query"]):
            if cand.page_id not in seen:
                seen.add(cand.page_id)
                candidates.append((cand, query))

    chosen = select_candidates(song, question, [c for c, _ in candidates], chat)
    for cand, query in candidates:
        if cand.page_id not in chosen:
            result.discarded.append(cand)
            continue
        page = wiki.fetch(cand.page_id)
        if len(page.text) >= cfg["min_doc_chars"]:
            result.indexed.append(CollectedDoc(page, query, False))
        else:
            result.discarded.append(cand)

    cache.add(song.song_id, pending, [d.page.page_id for d in result.indexed])
    return result
