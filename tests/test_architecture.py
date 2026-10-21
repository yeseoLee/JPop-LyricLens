import ast

NON_DOMAIN = ["collect", "index", "rag", "services"]


def test_domain_code_isolated(repo_root):
    """T-NF2005-1 도메인 외 패키지는 utaten 모듈을 import하지 않는다."""
    pkg = repo_root / "src/lyriclens"
    assert pkg.is_dir()
    bad = []
    for sub in NON_DOMAIN:
        assert (pkg / sub / "__init__.py").exists(), f"{sub} 패키지 없음"
        for py in (pkg / sub).rglob("*.py"):
            tree = ast.parse(py.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                names = []
                if isinstance(node, ast.Import):
                    names = [a.name for a in node.names]
                elif isinstance(node, ast.ImportFrom) and node.module:
                    names = [node.module] + [f"{node.module}.{a.name}" for a in node.names]
                bad += [f"{py.name}: {n}" for n in names if "utaten" in n]
    assert bad == []
