# AGENTS.md — 에이전트 작업 규칙

이 저장소에서 일하는 모든 코딩 에이전트(Claude Code 등)와 사람은 아래 규칙을 따른다.
서비스 정의는 `docs/SPEC.md` 를 기준으로 한다.

## 1. 원칙

1. **SPEC 우선 (Spec Driven)**: SPEC에 없는 기능은 만들지 않는다. 새 기능이나 동작 변경이 필요하면 먼저 SPEC을 쓰거나 고친다.
2. **테스트 우선 (Test Driven)**: SPEC의 수용 기준(AC)을 테스트로 먼저 쓰고, 실패하는 것을 확인한 다음 구현한다.
3. **MVP는 PRD에 대응한다**: MVP SPEC 항목은 반드시 PRD 요구사항 번호(F20xx, NF20xx)를 가진다. 확장 SPEC(`X-xx`)은 PRD와 무관해도 된다.
4. **모든 문서·이슈·PR·커밋 메시지 본문은 한국어**로 쓴다. (코드 식별자는 영어)

## 2. 작업 흐름

한 이슈 = 한 브랜치 = 한 PR. 아래 순서를 건너뛰지 않는다.

```
① ISSUE SPEC 작성 → ② 브랜치 생성·SPEC 커밋 → ③ 테스트 작성 → ④ 코드 작업
→ ⑤ PR → ⑥ CI 테스트 → ⑦ (통과 시) 리뷰 에이전트 리뷰 → ⑧ 리뷰 반영·머지 → ⑨ ISSUE 닫기
```

### ① ISSUE SPEC 작성
- `docs/specs/_TEMPLATE.md` 를 복사해 `docs/specs/SPEC-<번호3자리>-<slug>.md` 를 만든다. 내용은 `docs/SPEC.md` 해당 절을 옮겨 상세화한다.
- GitHub 이슈를 연다: `gh issue create --template spec.md` (제목: `[SPEC-XXX] <기능명>`). 본문에 대응 요구사항 번호, 범위, AC 목록을 적는다.
- SPEC을 쓰다 사용자 결정이 필요한 부분이 나오면 **추측하지 말고 사용자에게 묻고**, 결정은 `docs/SPEC.md` 0절 의사결정 기록에 추가한다.

### ② 브랜치 생성·SPEC 커밋
- `main` 에서 분기: `feat/<이슈번호>-<slug>` (버그: `fix/…`, 문서: `docs/…`, 설정: `chore/…`)
- 첫 커밋은 SPEC만 담는다: `docs(spec): SPEC-XXX <기능명> (#이슈번호)`
- `docs/SPEC.md` 를 바꿨다면 같은 커밋에 넣는다.

### ③ 테스트 작성
- AC마다 테스트를 하나 이상 쓴다. 테스트 docstring 첫 줄에 테스트 ID(예: `T-F2006-1`)를 쓴다.
- `pytest` 로 **실패하는 것을 확인**한 뒤 커밋: `test: SPEC-XXX 수용 기준 테스트 (#이슈번호)`
- 외부 호출(utaten, 위키백과, LLM, 임베딩)은 `tests/fakes.py` 대역을 쓴다. 실제 호출 테스트는 `@pytest.mark.live`.

### ④ 코드 작업
- 테스트를 통과시키는 최소 구현 → 리팩터링. 커밋: `feat: …`, `fix: …`, `refactor: …` (+ `(#이슈번호)`)
- 로컬 확인: `ruff check . && pytest -m "not live"`
- 구현 중 SPEC과 다르게 해야 할 이유가 생기면 **코드보다 SPEC을 먼저 고치고** 커밋한다.

### ⑤ PR
- `gh pr create --base main` , 템플릿(`.github/pull_request_template.md`)을 채운다.
- 본문에 `Closes #이슈번호`, 대응 요구사항, AC ↔ 테스트 대조표를 넣는다.

### ⑥ CI 테스트
- `.github/workflows/ci.yml` 이 PR마다 `ruff check` 와 `pytest -m "not live"` 를 실행한다.
- `gh pr checks <PR번호> --watch` 로 결과를 기다린다. 실패하면 고쳐서 같은 브랜치에 push 하고 다시 기다린다. **CI가 통과하기 전에는 리뷰를 요청하지 않는다.**

### ⑦ 리뷰 에이전트 리뷰
- CI 통과 후 `reviewer` 서브에이전트(`.claude/agents/reviewer.md`)에게 PR 번호를 주고 리뷰를 요청한다.
- 리뷰 에이전트는 SPEC 준수·테스트 충분성·보안(NF2003/NF2004)·출처 규칙(NF2006/NF2007)을 확인하고 `gh pr review <번호> --comment` 로 결과를 남긴다. 결론은 `APPROVE` 또는 `CHANGES_REQUESTED` 중 하나로 본문 첫 줄에 쓴다.

### ⑧ 리뷰 반영·머지
- `CHANGES_REQUESTED` 면 반영 커밋을 push → CI 재통과 → 다시 ⑦.
- `APPROVE` 이고 CI가 초록이면: `gh pr merge <번호> --squash --delete-branch`

### ⑨ ISSUE 닫기
- `Closes #N` 으로 자동으로 닫혔는지 `gh issue view N` 으로 확인하고, 안 닫혔으면 `gh issue close N --comment "PR #M 머지로 완료"`.
- 해당 SPEC 파일의 상태를 `완료` 로 바꾸는 일은 다음 이슈 브랜치의 SPEC 커밋에 함께 넣어도 된다.

## 3. 코드 규칙

- Python 3.12, 의존성은 `requirements.txt`(PRD 고정 버전) / `requirements-dev.txt`. 새 패키지는 SPEC 2.3 표에 이유를 적은 뒤 추가한다.
- 디렉터리 책임은 `docs/SPEC.md` 2.2를 따른다. utaten·J-POP에 묶인 코드는 `src/lyriclens/domain/` 에만 둔다.
- 청크 크기·Top-k·모델명·호출 간격 같은 값은 코드에 쓰지 않고 `config/settings.yaml` 에서 읽는다.
- 프롬프트는 `src/lyriclens/rag/prompts.py` 에 모은다.
- 사용자에게 보이는 문구는 `src/lyriclens/ui/messages.py` 에 모은다. 예외 추적 정보·프롬프트 전문·키를 화면에 내보내지 않는다.

## 4. 보안·데이터 규칙

- `.env`, API 키, `data/`(원본 HTML·가사·Chroma)는 **절대 커밋하지 않는다**. 커밋 전 `git status` 로 확인한다.
- 테스트 픽스처에 실제 가사를 넣지 않는다. utaten 구조를 흉내 낸 합성 HTML과 직접 지은 가사를 쓴다.
- utaten 호출 간격 3초 이상, 위키백과 1초 이상, User-Agent에 `WIKI_CONTACT` 연락처를 넣는다.
- 화면의 가사 인용은 `display.lyrics_quote_max_lines` 줄 이하로 제한하고 원문 링크를 함께 둔다.

## 5. 커밋·PR 형식

- 커밋 제목: `<type>(<scope>): <요약> (#이슈)` — type: `docs, test, feat, fix, refactor, chore, ci`
- 하나의 커밋은 하나의 의도만 담는다. SPEC 커밋 → 테스트 커밋 → 구현 커밋 순서가 히스토리에 보여야 한다.
- `main` 에 직접 push 하지 않는다. (초기 저장소 설정 커밋만 예외)
