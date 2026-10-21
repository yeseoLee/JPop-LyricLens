"""RAG 사용 전후 비교 문서의 표·대표 질문 부분 생성 (SPEC-018).

    python scripts/rag_comparison_report.py data/bench/results/<시각>-qa.json > 표.md
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from lyriclens.bench.cases import load_qa_cases  # noqa: E402
from lyriclens.bench.comparison import comparison_markdown  # noqa: E402


def main() -> int:
    report = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    cases = {c["id"]: c for c in load_qa_cases(ROOT / "bench/qa_cases.yaml")}
    print(comparison_markdown(report, cases))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
