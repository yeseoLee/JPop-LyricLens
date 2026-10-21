import re
import subprocess

KEY_PATTERNS = [re.compile(r"sk-[A-Za-z0-9_-]{20,}"), re.compile(r"GMS_KEY[ \t]*=[ \t]*[A-Za-z0-9_\-]{16,}")]


def _tracked(repo_root):
    out = subprocess.run(["git", "ls-files"], cwd=repo_root, capture_output=True, text=True)
    return [line for line in out.stdout.splitlines() if line]


def test_no_secret_in_tracked_files(repo_root):
    """T-NF2003-2 추적 파일에 API 키 패턴이 없다."""
    hits = []
    for rel in _tracked(repo_root):
        path = repo_root / rel
        if path.suffix in {".png", ".jpg", ".pdf"} or not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pat in KEY_PATTERNS:
            for m in pat.finditer(text):
                hits.append(f"{rel}: {m.group(0)[:12]}…")
    assert hits == []


def test_env_and_data_not_tracked(repo_root):
    """T-NF2007-1 .env 와 data/ 는 git에 추적되지 않는다."""
    tracked = _tracked(repo_root)
    assert ".env" not in tracked
    assert not [p for p in tracked if p.startswith("data/")]
