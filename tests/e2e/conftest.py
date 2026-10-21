"""E2E 픽스처 — 앱 서버를 띄우고 브라우저 페이지를 준다 (SPEC-012 §3.1)."""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest
import requests

ROOT = Path(__file__).resolve().parents[2]
SHOTS = ROOT / "docs" / "e2e"


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _preconditions() -> str | None:
    from lyriclens.config import load_settings, missing_env

    settings = load_settings()
    if missing_env(settings):
        return f"환경변수 없음: {missing_env(settings)}"
    import chromadb

    try:
        col = chromadb.PersistentClient(path=str(settings.path("chroma"))).get_collection(
            "song_meta"
        )
    except Exception:
        return "song_meta 색인 없음 — scripts/index_songs.py 를 먼저 실행"
    return None if col.count() else "song_meta 색인 0건"


@pytest.fixture(scope="session")
def app_url():
    reason = _preconditions()
    if reason:
        pytest.skip(reason)
    port = _free_port()
    proc = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", str(ROOT / "src/lyriclens/ui/app.py"),
         "--server.headless", "true", "--server.port", str(port),
         "--browser.gatherUsageStats", "false"],
        cwd=ROOT, env=os.environ.copy(),
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    url = f"http://127.0.0.1:{port}"
    try:
        for _ in range(120):
            if proc.poll() is not None:
                pytest.fail("앱 서버가 시작 중에 종료되었습니다")
            try:
                if requests.get(f"{url}/_stcore/health", timeout=1).text == "ok":
                    break
            except requests.RequestException:
                pass
            time.sleep(0.5)
        else:
            pytest.fail("앱 서버가 60초 안에 뜨지 않았습니다")
        yield url
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()


@pytest.fixture(scope="session")
def browser():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        b = p.chromium.launch()
        yield b
        b.close()


@pytest.fixture(scope="module")
def page(browser, app_url):
    """모듈 안의 시나리오는 한 세션(같은 대화 기록)을 이어서 쓴다."""
    context = browser.new_context(viewport={"width": 1440, "height": 1000}, locale="ko-KR")
    pg = context.new_page()
    pg.set_default_timeout(120_000)
    pg.goto(app_url)
    pg.get_by_text("곡 색인:").wait_for()
    yield pg
    context.close()


def shot(page, name: str) -> Path:
    SHOTS.mkdir(parents=True, exist_ok=True)
    path = SHOTS / name
    page.screenshot(path=str(path), full_page=True)
    return path


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """실패한 시나리오는 화면을 docs/e2e/failed_<이름>.png 로 남긴다."""
    outcome = yield
    report = outcome.get_result()
    page = item.funcargs.get("page")
    if report.when == "call" and report.failed and page is not None:
        shot(page, f"failed_{item.name}.png")
