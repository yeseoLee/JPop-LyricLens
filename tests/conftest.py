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

    if not os.environ.get("GMS_BASE_URL"):
        monkeypatch.setenv("GMS_BASE_URL", "https://example.invalid/v1/")
