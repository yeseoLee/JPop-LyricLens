from lyriclens.config import load_artists, load_settings, missing_env


def test_default_settings():
    """T-CFG-1 기본 설정값을 읽는다."""
    s = load_settings()
    assert s.chunking["chunk_size"] == 1000
    assert s.chunking["chunk_overlap"] == 200
    assert s.retrieval["wiki_top_k"] == 5
    assert s.display["lyrics_quote_max_lines"] == 4
    assert s.crawl["request_interval_sec"] >= 3.0


def test_overrides_merge_by_section():
    """T-CFG-2 overrides는 섹션 단위로 병합된다."""
    s = load_settings(overrides={"chunking": {"chunk_size": 500}})
    assert s.chunking["chunk_size"] == 500
    assert s.chunking["chunk_overlap"] == 200


def test_settings_path_from_env(tmp_path, monkeypatch, repo_root):
    """T-CFG-3 LYRICLENS_SETTINGS로 다른 설정 파일을 지정한다."""
    text = (repo_root / "config/settings.yaml").read_text(encoding="utf-8")
    alt = tmp_path / "alt.yaml"
    alt.write_text(text.replace("wiki_top_k: 5", "wiki_top_k: 9"), encoding="utf-8")
    monkeypatch.setenv("LYRICLENS_SETTINGS", str(alt))
    assert load_settings().retrieval["wiki_top_k"] == 9


def test_missing_key_detected_and_hidden(monkeypatch):
    """T-NF2003-1 키 누락을 감지하고 repr에 키 값을 노출하지 않는다."""
    monkeypatch.setenv("GMS_KEY", "")
    monkeypatch.setenv("WIKI_CONTACT", "a@b.c")
    assert "GMS_KEY" in missing_env(load_settings())

    monkeypatch.setenv("GMS_KEY", "secret-value-123")
    s = load_settings()
    assert missing_env(s) == []
    assert "secret-value-123" not in repr(s)


def test_path_is_absolute():
    """T-CFG-1 paths 값은 프로젝트 루트 기준 절대 경로로 변환된다."""
    p = load_settings().path("songs")
    assert p.is_absolute() and p.name == "songs.jsonl"


def test_load_artists():
    """T-CFG-4 아티스트 목록 40명을 읽는다."""
    artists = load_artists()
    assert len(artists) == 40
    assert all(a["name"] and a["name_ko"] for a in artists)
    assert len({a["name"] for a in artists}) == 40


def test_unknown_override_section_rejected():
    """T-CFG-2 알 수 없는 섹션 overrides는 ValueError."""
    import pytest

    with pytest.raises(ValueError):
        load_settings(overrides={"chunkin": {"chunk_size": 1}})
