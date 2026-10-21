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
