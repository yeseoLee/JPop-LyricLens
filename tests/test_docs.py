import re
from pathlib import Path

REQS = [f"F20{n:02d}" for n in range(1, 13)] + [f"NF200{n}" for n in range(1, 8)]


def _read(repo_root: Path, rel: str) -> str:
    return (repo_root / rel).read_text(encoding="utf-8")


def test_traceability_rows(repo_root):
    """T-DOC-1 대조표에 필수·비기능 요구사항이 모두 있다."""
    text = _read(repo_root, "docs/verification.md")
    for req in REQS:
        assert re.search(rf"^\|\s*{req}\s*\|", text, re.M), req


def test_traceability_ids_exist(repo_root):
    """T-DOC-2 대조표의 테스트 ID가 실제 테스트에 있다."""
    table = _read(repo_root, "docs/verification.md")
    ids = set(re.findall(r"T-[A-Z0-9]+-\d+", table))
    in_tests = set()
    for py in (repo_root / "tests").glob("test_*.py"):
        in_tests |= set(re.findall(r"T-[A-Z0-9]+-\d+", py.read_text(encoding="utf-8")))
    assert ids and ids <= in_tests, sorted(ids - in_tests)


def test_readme(repo_root):
    """T-DOC-3 README에 실행 명령과 출처 절이 있다."""
    text = _read(repo_root, "README.md")
    for cmd in ["pip install -r requirements.txt", "scripts/crawl_songs.py",
                "scripts/index_songs.py", "streamlit run src/lyriclens/ui/app.py"]:
        assert cmd in text
    assert "출처와 이용 조건" in text


def test_pipeline_doc(repo_root):
    """T-DOC-4 설계문서에 컬렉션과 프롬프트 설명이 있다."""
    text = _read(repo_root, "docs/rag_pipeline.md")
    for name in ["song_meta", "wiki_docs", "song_lyrics", "프롬프트 1", "프롬프트 2", "프롬프트 3"]:
        assert name in text
