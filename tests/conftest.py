from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def repo_root() -> Path:
    return ROOT


@pytest.fixture(autouse=True)
def _gms_base_url(monkeypatch):
    """GMS_BASE_URL 은 .env 로 관리한다. 테스트에는 가짜 주소를 기본으로 둔다."""
    import os

    from dotenv import dotenv_values

    # 실제 .env 에 값이 있으면 그대로 둔다 (live 테스트가 가짜 주소를 쓰지 않게)
    if not os.environ.get("GMS_BASE_URL") and not dotenv_values(ROOT / ".env").get("GMS_BASE_URL"):
        monkeypatch.setenv("GMS_BASE_URL", "https://example.invalid/v1/")
