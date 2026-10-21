import re
from pathlib import Path

from lyriclens.config import load_settings
from lyriclens.ui import messages
from lyriclens.ui.env import check_environment


def test_environment_states(monkeypatch):
    """T-F2012-1 키 없음 / 색인 0건 / 정상, 연락처 없음은 경고."""
    monkeypatch.setenv("GMS_KEY", "")
    monkeypatch.setenv("WIKI_CONTACT", "")
    assert check_environment(load_settings(), 240).status == "missing_key"
    monkeypatch.setenv("GMS_KEY", "k" * 20)
    env = check_environment(load_settings(), 0)
    assert env.status == "no_index" and "missing_contact" in env.warnings
    monkeypatch.setenv("WIKI_CONTACT", "a@b.c")
    env = check_environment(load_settings(), 240)
    assert env.status == "ok" and env.warnings == []


def test_no_internal_info_exposed(repo_root: Path):
    """T-F2012-2 화면 문구와 앱 코드에 내부 정보 노출 경로가 없다."""
    texts = [v for k, v in vars(messages).items() if k.isupper() and isinstance(v, str)]
    assert texts
    for t in texts:
        assert "Traceback" not in t and not re.search(r"sk-\w{10,}", t) and "{key}" not in t
    app = (repo_root / "src/lyriclens/ui/app.py").read_text(encoding="utf-8")
    assert "st.exception" not in app and "traceback" not in app
    assert "SYSTEM" not in app  # 프롬프트 전문을 화면에 쓰지 않는다
