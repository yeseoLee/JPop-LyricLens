"""화면과 기능 사이의 서비스 계층 — 진행 단계 콜백과 오류 격리 (SPEC-010 §3.4)."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from lyriclens.collect.models import SongInfo
from lyriclens.collect.pipeline import IndexedCollectResult, collect_and_index
from lyriclens.http import FetchError
from lyriclens.rag.evidence import Evidence
from lyriclens.rag.generate import Answer, generate_answer
from lyriclens.rag.retrieve import SONG_LYRICS, SONG_META, retrieve
from lyriclens.services.condition_search import search_by_condition
from lyriclens.services.phrase_interpret import interpret_phrase
from lyriclens.services.phrase_search import search_phrase

log = logging.getLogger(__name__)


@dataclass
class AskResult:
    answer: Answer
    evidence: list[Evidence]
    collect: IndexedCollectResult | None


class LyricLensService:
    def __init__(self, settings, store, chat, wiki, cache):
        self.settings, self.store, self.chat, self.wiki, self.cache = (
            settings, store, chat, wiki, cache
        )

    # 곡 정보 -------------------------------------------------------------
    def song_metas(self) -> list[dict]:
        if self.store.count(SONG_META) == 0:
            return []
        res = self.store.collection(SONG_META)._collection.get(include=["metadatas"])
        return [md for md in res["metadatas"] if md]

    def song_meta(self, song_id: str) -> dict:
        docs = self.store.get(SONG_META, [song_id])
        return docs[0].metadata if docs else {}

    def stanzas(self, song_id: str):
        return self.store.get_where(SONG_LYRICS, {"song_id": song_id})

    def song_info(self, song_id: str) -> SongInfo:
        md = self.song_meta(song_id)
        return SongInfo(song_id, md.get("title", ""), md.get("artist", ""),
                        md.get("artist_ko"), md.get("tieup"))

    # 질문하기 (F2003~F2008) ----------------------------------------------
    def ask(self, song_id: str, question: str, history, on_step=lambda step, detail: None):
        song = self.song_info(song_id)
        collected = None
        try:
            on_step("queries", song.title)
            collected = collect_and_index(song, question, self.chat, self.wiki, self.cache,
                                          self.store, self.settings)
            on_step("collect", collected)
            on_step("index", collected.chunk_count)
        except FetchError:
            log.exception("위키 수집 실패: %s", song_id)
            on_step("collect_failed", None)
        evidence = retrieve(self.store, song_id, question, self.settings)
        on_step("answer", None)
        answer = generate_answer(question, evidence, self.chat, self.settings, history)
        return AskResult(answer, evidence, collected)

    # 특화 기능·탐색 --------------------------------------------------------
    def condition_search(self, condition: str):
        return search_by_condition(condition, self.store, self.chat, self.settings)

    def interpret(self, song_id: str, phrase: str, target_lang: str):
        return interpret_phrase(song_id, phrase, target_lang, self.store, self.chat,
                                self.settings)

    def phrase_search(self, text: str):
        return search_phrase(text, self.store, self.chat, self.settings)
