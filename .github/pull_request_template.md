## 요약
-

Closes #

## 대응 SPEC / 요구사항
- SPEC: `docs/specs/SPEC-XXX-<slug>.md`
- PRD: F20xx, NF20xx

## AC ↔ 테스트 대조
| 테스트 ID | 테스트 함수 | 결과 |
|-----------|-------------|------|
| T-F20xx-1 | `tests/...::test_...` | 통과 |

## 확인
- [ ] 커밋 순서: SPEC → 테스트 → 구현
- [ ] `ruff check .` / `pytest -m "not live"` 로컬 통과
- [ ] `.env`, `data/`, 실제 가사가 포함되지 않음
- [ ] 설정값·프롬프트·화면 문구를 정해진 모듈에 둠
