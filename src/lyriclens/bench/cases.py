"""벤치마크 케이스 로드·검증·정답 해석 (SPEC-015 §3, §4)."""

from __future__ import annotations

from pathlib import Path

import yaml

from lyriclens.domain.lyrics import split_stanzas

LANGS = {"ko", "en", "ja"}
SPLITS = {"dev", "test"}
QA_TYPES = {"credit", "release", "tieup", "background", "meaning", "unanswerable"}
MIN_COUNTS = {
    "title_ja": 15, "title_ko": 12, "title_en": 12, "artist_ja": 10, "artist_ko": 10,
    "artist_en": 8, "nickname": 12, "abbrev": 10, "typo": 20, "lyrics_ja": 20,
    "lyrics_ko": 15, "lyrics_en": 10, "semantic": 15, "tieup": 12, "mixed": 10,
}
LYRICS_CHUNK_LINES = 8  # song_lyrics 와 같은 연 분할 (settings.chunking.lyrics_chunk_lines)


def _load(path: str | Path) -> list[dict]:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8")) or []


load_search_cases = load_lyric_refs = load_qa_cases = _load


def validate_cases(search: list[dict], refs: list[dict], qa: list[dict],
                   min_counts: dict[str, int] = MIN_COUNTS) -> list[str]:
    errors: list[str] = []
    seen: set[str] = set()
    counts: dict[str, int] = {}
    for c in search + refs + qa:
        cid = c.get("id", "?")
        if cid in seen:
            errors.append(f"{cid}: id 중복")
        seen.add(cid)
        if c.get("lang") not in LANGS:
            errors.append(f"{cid}: lang 은 ko/en/ja 중 하나")
        if c.get("split") not in SPLITS:
            errors.append(f"{cid}: split 은 dev/test 중 하나")
    for c in search:
        counts[c.get("category")] = counts.get(c.get("category"), 0) + 1
        if not c.get("query"):
            errors.append(f"{c.get('id')}: query 없음")
        if bool(c.get("relevant")) == bool(c.get("relevant_artist")):
            errors.append(f"{c.get('id')}: relevant 또는 relevant_artist 중 하나만 필요")
    for r in refs:
        counts[r.get("category")] = counts.get(r.get("category"), 0) + 1
        if not (r.get("song") and isinstance(r.get("stanza"), int)
                and isinstance(r.get("line"), int)):
            errors.append(f"{r.get('id')}: song/stanza/line 필요")
    for q in qa:
        if q.get("type") not in QA_TYPES:
            errors.append(f"{q.get('id')}: type 오류")
        groups = q.get("answer_keywords")
        if q.get("type") != "unanswerable" and not (
            groups and all(isinstance(g, list) and g for g in groups)
        ):
            errors.append(f"{q.get('id')}: answer_keywords 필요")
    for cat, need in min_counts.items():
        if counts.get(cat, 0) < need:
            errors.append(f"{cat}: {counts.get(cat, 0)}개 (최소 {need})")
    return errors


def _index(songs: list[dict]):
    by_key = {(s["title"], s["artist"]): s["song_id"] for s in songs}
    by_artist: dict[str, list[str]] = {}
    for s in songs:
        by_artist.setdefault(s["artist"], []).append(s["song_id"])
    return by_key, by_artist


def resolve_cases(cases: list[dict], songs: list[dict]) -> tuple[list[dict], list[str]]:
    """relevant / relevant_artist 를 relevant_ids 로 바꾼다. (케이스, 못 찾은 항목)"""
    by_key, by_artist = _index(songs)
    out, missing = [], []
    for c in cases:
        if c.get("relevant_artist"):
            ids = by_artist.get(c["relevant_artist"], [])
            if not ids:
                missing.append(f"{c['id']}: {c['relevant_artist']}")
        else:
            ids = []
            for r in c["relevant"]:
                sid = by_key.get((r["title"], r["artist"]))
                if sid:
                    ids.append(sid)
                else:
                    missing.append(f"{c['id']}: {r['title']} / {r['artist']}")
        out.append({**c, "relevant_ids": ids})
    return out, missing


def lyric_line(song: dict, stanza: int, line: int) -> str | None:
    stanzas = split_stanzas(song["lyrics"], LYRICS_CHUNK_LINES)
    if stanza >= len(stanzas):
        return None
    lines = stanzas[stanza].splitlines()
    return lines[line] if line < len(lines) else None


def materialize_lyric_queries(refs: list[dict], songs: list[dict],
                              translations: dict[str, str]) -> tuple[list[dict], list[str]]:
    """가사 참조를 질의 케이스로. ja 는 원문 줄, ko/en 은 translations[id] (없으면 빠짐)."""
    by_key, _ = _index(songs)
    by_id = {s["song_id"]: s for s in songs}
    out, missing = [], []
    for r in refs:
        sid = by_key.get((r["song"]["title"], r["song"]["artist"]))
        text = lyric_line(by_id[sid], r["stanza"], r["line"]) if sid else None
        if text is None:
            missing.append(r["id"])
            continue
        query = text if r["lang"] == "ja" else translations.get(r["id"])
        if not query:
            missing.append(r["id"])
            continue
        out.append({"id": r["id"], "category": r["category"], "lang": r["lang"],
                    "split": r["split"], "query": query, "relevant_ids": [sid],
                    "source_line": text})
    return out, missing
