"""JPop LyricLens Streamlit 화면 (SPEC-010).

    streamlit run src/lyriclens/ui/app.py
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from lyriclens.collect.cache import CollectCache  # noqa: E402
from lyriclens.collect.wikipedia import WikiClient  # noqa: E402
from lyriclens.config import load_settings  # noqa: E402
from lyriclens.index.store import VectorStore  # noqa: E402
from lyriclens.llm import make_chat, make_embeddings  # noqa: E402
from lyriclens.rag.citations import preview  # noqa: E402
from lyriclens.rag.retrieve import SONG_META  # noqa: E402
from lyriclens.ui import messages as msg  # noqa: E402
from lyriclens.ui.env import check_environment  # noqa: E402
from lyriclens.ui.service import LyricLensService  # noqa: E402
from lyriclens.ui.state import ChatStore, song_options, stanza_options  # noqa: E402

log = logging.getLogger("lyriclens.ui")


def _setup_logging(settings) -> None:
    log_dir = settings.root / "data" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    if not logging.getLogger().handlers:
        logging.basicConfig(filename=log_dir / "app.log", level=logging.INFO,
                            format="%(asctime)s %(levelname)s %(name)s %(message)s")


@st.cache_resource
def _service(_settings) -> LyricLensService:
    store = VectorStore(_settings.path("chroma"), make_embeddings(_settings))
    wiki = WikiClient(contact=_settings.wiki_contact,
                      interval_sec=_settings.collect["request_interval_sec"],
                      max_retries=_settings.collect["max_retries"])
    return LyricLensService(_settings, store, make_chat(_settings), wiki,
                            CollectCache(_settings.path("collect_cache")),
                            aux_chat=make_chat(_settings, aux=True))


def _safe(fn, *args, **kwargs):
    """서비스 호출을 감싸 화면에는 일반 문구만 보여 준다 (NF2004)."""
    try:
        return fn(*args, **kwargs)
    except Exception:
        log.exception("서비스 호출 실패")
        st.error(msg.GENERIC_ERROR)
        return None


def _render_evidence(citations, no_citation: bool, max_lines: int) -> None:
    if no_citation or not citations:
        st.caption(msg.NO_CITATION)
        return
    with st.expander(msg.EVIDENCE_HEADER.format(count=len(citations))):
        for ev in citations:
            link = f" · [원문]({ev.url})" if ev.url else ""
            st.markdown(f"**[근거 {ev.num}]** {ev.title} · {ev.label}{link}")
            st.text(preview(ev, max_lines))


def _select_song(song_id: str, title: str) -> None:
    st.session_state["song_id"] = song_id
    st.session_state["switched"] = title


def _sidebar(service, settings, options) -> str | None:
    with st.sidebar:
        st.header(msg.SIDEBAR_SELECT)
        labels = {sid: label for label, sid in options}
        ids = [sid for _, sid in options]
        current = st.session_state.get("song_id")
        song_id = st.selectbox(
            msg.SIDEBAR_SELECT, ids, index=ids.index(current) if current in ids else None,
            format_func=lambda sid: labels.get(sid, sid), placeholder=msg.SIDEBAR_PLACEHOLDER,
            label_visibility="collapsed",
        )
        if song_id:
            st.session_state["song_id"] = song_id
            meta = service.song_meta(song_id)
            if meta.get("tieup"):
                st.caption(f"🎬 {meta['tieup']}")
            if meta.get("url"):
                st.markdown(f"[{msg.ORIGINAL_LINK}]({meta['url']})")
        st.divider()
        st.caption(msg.INDEX_COUNT.format(count=len(options)))
        st.caption(msg.COPYRIGHT_NOTICE)
        st.caption(msg.TRANSLATION_NOTICE)
    return song_id


def _chat_tab(service, settings, chats: ChatStore, song_id: str | None) -> None:
    if not song_id:
        st.info(msg.SELECT_SONG_FIRST)
        return
    max_lines = settings.display["lyrics_quote_max_lines"]
    for m in chats.messages(song_id):
        with st.chat_message(m["role"]):
            st.markdown(m["content"])
            if m["role"] == "assistant":
                _render_evidence(m.get("citations", []), m.get("no_citation", True), max_lines)

    question = st.chat_input(msg.CHAT_PLACEHOLDER)
    if not question:
        return
    history = chats.history(song_id)
    chats.add(song_id, "user", question)
    with st.chat_message("user"):
        st.markdown(question)
    with st.chat_message("assistant"):
        with st.status(msg.STEP_RUNNING, expanded=True) as status:
            def on_step(step, detail):
                if step == "queries":
                    st.write(msg.STEP_QUERIES.format(detail=detail))
                elif step == "collect":
                    titles = ", ".join(d.page.title for d in detail.indexed) or "-"
                    st.write(msg.STEP_COLLECT.format(detail=titles))
                    if detail.cached_queries:
                        st.write(msg.STEP_COLLECT_CACHED.format(count=len(detail.cached_queries)))
                elif step == "collect_failed":
                    st.write(msg.STEP_COLLECT_FAILED)
                elif step == "index":
                    st.write(msg.STEP_INDEX.format(count=detail))
                elif step == "answer":
                    st.write(msg.STEP_ANSWER)

            prepared = _safe(service.prepare, song_id, question, on_step=on_step)
            status.update(label=msg.STEP_DONE, state="complete", expanded=False)
        if prepared is None:
            return
        evidence, _ = prepared
        if not any(e.source_type == "wikipedia" for e in evidence):
            st.caption(msg.NO_WIKI_DOCS)
        final: list = []

        def pieces():
            for item in service.answer_stream(question, evidence, history):
                if isinstance(item, str):
                    yield item
                else:
                    final.append(item)

        streamed = _safe(st.write_stream, pieces)
        if streamed is None or not final:
            return
        answer = final[0]
        if not isinstance(streamed, str) or not streamed:  # 근거가 없어 조각 없이 끝난 경우
            st.markdown(answer.text)
        _render_evidence(answer.cited, answer.no_citation, max_lines)
        chats.add(song_id, "assistant", answer.text, citations=answer.cited,
                  no_citation=answer.no_citation)


def _condition_tab(service) -> None:
    condition = st.text_input(msg.CONDITION_INPUT, key="condition")
    if st.button(msg.SEARCH_BUTTON, key="condition_btn") and condition:
        st.session_state["condition_result"] = _safe(service.condition_search, condition)
    result = st.session_state.get("condition_result")
    if result is None:
        return
    if result.status == "empty":
        st.info(msg.CONDITION_EMPTY)
    for m in result.matches:
        with st.container(border=True):
            year = f" ({m.year})" if m.year else ""
            st.markdown(f"**{m.title}** — {m.artist}{year}")
            st.caption(m.reason)
            st.button(msg.OPEN_CHAT, key=f"cond_{m.song_id}", on_click=_select_song,
                      args=(m.song_id, m.title))


def _interpret_tab(service, settings, song_id: str | None) -> None:
    if not song_id:
        st.info(msg.SELECT_SONG_FIRST)
        return
    options = stanza_options(_safe(service.stanzas, song_id) or [])
    picked = st.selectbox(msg.INTERPRET_PICK, [text for _, text in options], index=None,
                          format_func=lambda t: dict((v, k) for k, v in options).get(t, t))
    pasted = st.text_area(msg.INTERPRET_INPUT, key=f"paste_{song_id}")
    lang = st.radio(msg.INTERPRET_LANG, ["ko", "en"], horizontal=True,
                    format_func=lambda c: {"ko": "한국어", "en": "English"}[c])
    phrase = pasted.strip() or picked
    if not (st.button(msg.INTERPRET_BUTTON) and phrase):
        return
    with st.spinner(msg.STEP_RUNNING):
        res = _safe(service.interpret, song_id, phrase, lang)
    if res is None:
        return
    if res.status == "not_found":
        st.warning(msg.INTERPRET_NOT_FOUND)
        return
    st.markdown(f"**{msg.INTERPRET_ORIGINAL}**")
    st.text(res.original)
    st.markdown(f"**{msg.INTERPRET_TRANSLATION}**\n\n{res.translation}")
    if res.notes:
        st.markdown(f"**{msg.INTERPRET_NOTES}**\n" + "\n".join(f"- {n}" for n in res.notes))
    st.markdown(f"**{msg.INTERPRET_BACKGROUND}**\n\n{res.background}")
    _render_evidence(res.citations, not res.citations, settings.display["lyrics_quote_max_lines"])


def _phrase_tab(service) -> None:
    text = st.text_input(msg.PHRASE_INPUT, key="phrase")
    if st.button(msg.SEARCH_BUTTON, key="phrase_btn") and text:
        st.session_state["phrase_result"] = _safe(service.phrase_search, text)
    hits = st.session_state.get("phrase_result")
    if hits is None:
        return
    if not hits:
        st.info(msg.PHRASE_EMPTY)
    for h in hits:
        with st.container(border=True):
            st.markdown(f"**{h.title}** — {h.artist} · [{msg.ORIGINAL_LINK}]({h.url})")
            st.text(h.matched)
            st.button(msg.OPEN_CHAT, key=f"phrase_{h.song_id}", on_click=_select_song,
                      args=(h.song_id, h.title))


def main() -> None:
    st.set_page_config(page_title=msg.APP_TITLE, page_icon="🎵", layout="wide")
    settings = load_settings()
    _setup_logging(settings)
    st.title(msg.APP_TITLE)
    st.caption(msg.APP_CAPTION)

    env = check_environment(settings, 1)
    if env.status == "missing_key":
        st.error(msg.MISSING_KEY)
        return
    service = _safe(_service, settings)
    if service is None:
        return
    env = check_environment(settings, service.store.count(SONG_META))
    if "missing_contact" in env.warnings:
        st.warning(msg.MISSING_CONTACT)
    if env.status == "no_index":
        st.error(msg.NO_INDEX)
        return

    chats = st.session_state.setdefault("chats", ChatStore())
    song_id = _sidebar(service, settings, song_options(service.song_metas()))
    if st.session_state.pop("switched", None):
        st.success(msg.SWITCHED.format(title=service.song_meta(song_id).get("title", "")))

    tab_chat, tab_cond, tab_interp, tab_phrase = st.tabs(
        [msg.TAB_CHAT, msg.TAB_CONDITION, msg.TAB_INTERPRET, msg.TAB_PHRASE]
    )
    with tab_chat:
        _chat_tab(service, settings, chats, song_id)
    with tab_cond:
        _condition_tab(service)
    with tab_interp:
        _interpret_tab(service, settings, song_id)
    with tab_phrase:
        _phrase_tab(service)


main()
