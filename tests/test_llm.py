import pytest

from lyriclens.config import load_settings
from lyriclens.llm import MissingKeyError, make_chat, make_embeddings


def test_missing_key(monkeypatch):
    """T-LLM-1 키가 없으면 MissingKeyError."""
    monkeypatch.setenv("GMS_KEY", "")
    s = load_settings()
    with pytest.raises(MissingKeyError):
        make_embeddings(s)
    with pytest.raises(MissingKeyError):
        make_chat(s)


def test_null_temperature_not_passed(monkeypatch):
    """T-LLM-2 temperature가 null이면 모델 기본값을 쓰도록 전달하지 않는다."""
    monkeypatch.setenv("GMS_KEY", "k" * 20)
    chat = make_chat(load_settings())
    assert chat.temperature is None
    assert chat.model_name == "gpt-6-luna"
    chat0 = make_chat(load_settings(overrides={"llm": {"temperature": 0}}))
    assert chat0.temperature == 0


def test_embedding_model_from_settings(monkeypatch):
    """T-CFG-1 임베딩 모델은 설정값을 따른다."""
    monkeypatch.setenv("GMS_KEY", "k" * 20)
    assert make_embeddings(load_settings()).model == "text-embedding-3-large"
