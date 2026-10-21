"""GMS(OpenAI 호환) 채팅·임베딩 모델 생성 (SPEC-003 §3.4)."""

from __future__ import annotations

from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from lyriclens.config import Settings


class MissingKeyError(RuntimeError):
    pass


def _key(settings: Settings) -> str:
    if not settings.gms_key:
        raise MissingKeyError("GMS_KEY가 설정되지 않았습니다.")
    return settings.gms_key


def make_embeddings(settings: Settings) -> OpenAIEmbeddings:
    return OpenAIEmbeddings(
        model=settings.llm["embedding_model"],
        api_key=_key(settings),
        base_url=settings.llm["base_url"],
        check_embedding_ctx_length=False,
    )


def make_chat(settings: Settings, **kw) -> ChatOpenAI:
    return ChatOpenAI(
        model=settings.llm["chat_model"],
        api_key=_key(settings),
        base_url=settings.llm["base_url"],
        temperature=settings.llm.get("temperature", 0),
        **kw,
    )
