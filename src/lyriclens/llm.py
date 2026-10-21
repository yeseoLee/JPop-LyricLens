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


def make_chat(settings: Settings, aux: bool = False, **kw) -> ChatOpenAI:
    """aux=True 면 보조 작업용 빠른 모델 (D-11)."""
    model = settings.llm["aux_model"] if aux else settings.llm["chat_model"]
    temperature = settings.llm.get("aux_temperature" if aux else "temperature")
    if temperature is not None:  # 기본값만 허용하는 모델이 있어 null이면 보내지 않는다
        kw.setdefault("temperature", temperature)
    return ChatOpenAI(
        model=model,
        api_key=_key(settings),
        base_url=settings.llm["base_url"],
        **kw,
    )
