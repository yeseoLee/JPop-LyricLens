"""외부 문서 수집 흐름 — 검색어 추출 → 1차 문서 → 후보 선별 → 본문 수집 (SPEC-004 §3.5)."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from lyriclens.collect.cache import CollectCache
from lyriclens.collect.candidate_selector import select_candidates
from lyriclens.collect.models import (
    CollectedDoc,
    CollectResult,
    SongInfo,
    WikiCandidate,
    WikiPage,
)
from lyriclens.collect.query_extractor import extract_queries

SONG_WORDS = ("노래", "곡", "싱글")


def _is_song_page(title: str, song_title: str) -> bool:
    return title == song_title or title.startswith(f"{song_title} (")


def _is_disambiguation(title: str) -> bool:
    return "동음이의" in title


def _matches_title_rule(title: str, song: SongInfo) -> bool:
    """원제 규칙, 또는 '번역 제목 (아티스트의 노래)' 형태 (SPEC-013 §2-2)."""
    if _is_song_page(title, song.title):
        return True
    _, paren, inside = title.partition("(")
    artists = [a for a in (song.artist_ko, song.artist) if a]
    return bool(paren) and any(a in inside for a in artists) and any(
        w in inside for w in SONG_WORDS
    )


VERIFY_CHARS = 2000


def _mentions_song(page: WikiPage, song: SongInfo) -> bool:
    head = page.text[:VERIFY_CHARS]
    artists = [a for a in (song.artist_ko, song.artist) if a]
    return song.title in head and any(a in head for a in artists)


def find_song_page(song: SongInfo, wiki, limit: int,
                   verify_limit: int) -> tuple[WikiCandidate | None, WikiPage | None]:
    """곡 문서와 (확인하느라 받은 경우) 본문을 돌려준다 (SPEC-013)."""
    direct = wiki.find_page(song.title)
    if direct and _is_song_page(direct.title, song.title):  # 흔한 경우: 검색 없이 끝
        return direct, None
    candidates: list[WikiCandidate] = [direct] if direct else []
    queries = (song.title, f"{song.title} {song.artist_query}",
               f"{song.artist_query} 노래 {song.title}")
    for query in queries:
        candidates += wiki.search(query, limit)
    seen: set[int] = set()
    unique = [
        c for c in candidates
        if not _is_disambiguation(c.title) and not (c.page_id in seen or seen.add(c.page_id))
    ]
    titled = next((c for c in unique if _matches_title_rule(c.title, song)), None)
    if titled:
        return titled, None
    for cand in unique[:verify_limit]:
        page = wiki.fetch(cand.page_id)
        if _mentions_song(page, song):
            return cand, page
    return None, None


def primary_docs(song: SongInfo, wiki, cfg) -> list[tuple[WikiCandidate, str, WikiPage | None]]:
    found: list[tuple[WikiCandidate, str, WikiPage | None]] = []
    song_page, fetched = find_song_page(song, wiki, cfg["candidates_per_query"],
                                        cfg.get("primary_verify_limit", 3))
    if song_page:
        found.append((song_page, song.title, fetched))
    artist_page = wiki.find_page(song.artist_query)
    if artist_page and all(artist_page.page_id != c.page_id for c, _, _ in found):
        found.append((artist_page, song.artist_query, None))
    return found


def collect_documents(song: SongInfo, question: str, chat, wiki, cache: CollectCache,
                      settings) -> CollectResult:
    cfg = settings.collect
    skip_primary = cache.primary_done(song.song_id)
    # 검색어 추출(LLM)과 1차 문서 찾기(위키)는 서로 기다릴 필요가 없다 (SPEC-014 §2-1)
    with ThreadPoolExecutor(max_workers=2) as pool:
        queries_future = pool.submit(extract_queries, song, question, chat, cfg["max_queries"])
        primary_future = None if skip_primary else pool.submit(primary_docs, song, wiki, cfg)
        result = CollectResult(queries=queries_future.result())
        primary = primary_future.result() if primary_future else []
    result.cached_queries = [q for q in result.queries if cache.has_query(song.song_id, q)]
    pending = [q for q in result.queries if q not in result.cached_queries]

    known = cache.page_ids(song.song_id)
    seen: set[int] = set(known)

    for cand, query, page in primary:
        if cand.page_id not in seen:
            seen.add(cand.page_id)
            result.indexed.append(CollectedDoc(page or wiki.fetch(cand.page_id), query, True))
    if not pending:
        cache.add(song.song_id, [], [d.page.page_id for d in result.indexed])
        cache.mark_primary_done(song.song_id)
        return result

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
    cache.mark_primary_done(song.song_id)
    return result
