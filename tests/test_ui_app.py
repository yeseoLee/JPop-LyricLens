from streamlit.testing.v1 import AppTest

from lyriclens.ui import messages


def test_app_without_key_shows_guide(monkeypatch, repo_root):
    """T-F2012-5 키 없이 실행하면 설정 안내가 보이고 예외가 없다."""
    monkeypatch.setenv("GMS_KEY", "")
    at = AppTest.from_file(str(repo_root / "src/lyriclens/ui/app.py"), default_timeout=30)
    at.run()
    assert not at.exception
    shown = " ".join(e.value for e in at.error) + " ".join(e.value for e in at.warning)
    assert messages.MISSING_KEY.splitlines()[0] in shown
