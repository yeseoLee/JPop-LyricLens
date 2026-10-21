# SPEC-007 generate·LangGraph·근거 표시

- 상태: 진행 중
- 이슈: #7
- 구분: MVP
- 대응 요구사항: F2007, F2008
- 관련 절: `docs/SPEC.md` §F2007, §F2008

## 1. 목적
검색한 근거만으로 질문 언어에 맞춰 답하고, 답변에 실제로 인용한 근거만 골라 화면에 넘긴다.

## 2. 범위
- 포함: `rag/prompts.py`(프롬프트 3), `rag/language.py`(질문 언어 판별), `rag/generate.py`, `rag/citations.py`, `rag/graph.py`
- 제외: 화면 렌더링(SPEC-010)

## 3. 상세 설계

### 3.1 질문 언어 (`detect_language(text) -> "ko" | "ja" | "en"`)
- 한글이 있으면 `ko`, 없고 가나가 있으면 `ja`, 둘 다 없으면 `en`. 한자만 있는 문장은 `ja`.

### 3.2 프롬프트 3 — 답변 생성
- 시스템 규칙
  1. 아래 [근거]에 있는 내용만 사용한다. 일반 상식이나 추측으로 채우지 않는다.
  2. 근거로 확인되지 않는 부분은 "제공된 문서에서 확인되지 않습니다"(질문 언어로)라고 쓴다.
  3. 주요 주장마다 `[근거 N]` 을 붙인다. 번호는 [근거] 목록의 번호를 그대로 쓴다.
  4. 질문과 같은 언어(ko/en/ja)로 답한다.
  5. 가사 원문은 한 번에 최대 {quote_max_lines}줄까지만 인용하고, 번역할 때는 원문 한 줄과 번역을 함께 쓴다.
- 근거 블록 형식: `[근거 N] (곡 정보|가사|위키백과) 제목\n본문`
- 최근 대화(`history`, 최대 4개 메시지)를 근거 블록 앞에 넣어 이어지는 질문을 이해하게 한다.
- **답변 언어는 코드가 정해 명시한다** (#26): `detect_language(question)` 결과를 `한국어 / English / 日本語` 로 바꿔 시스템 프롬프트의 `답변 언어: …` 줄과 사람 메시지 끝 `(답변 언어: …)` 에 넣는다. "질문과 같은 언어" 규칙만으로는 한국어 프롬프트·근거에 끌려 한국어로 답하는 문제가 실제 실행에서 확인됨.

### 3.3 생성 (`generate_answer(question, evidence, chat, settings, history=()) -> Answer`)
```python
@dataclass
class Answer:
    text: str
    cited: list[Evidence]     # 본문에서 인용된 근거만, 번호순
    no_citation: bool         # 인용이 하나도 없으면 True → 화면 안내
```
- 근거가 0개면 LLM을 부르지 않고 질문 언어의 "확인되지 않습니다" 문구를 돌려준다(`no_citation=True`). 문구는 `prompts.NOT_FOUND`.

### 3.4 근거 표시 (`rag/citations.py`)
- `cited_numbers(text) -> list[int]`: `[근거 N]`, `[Source N]`, `[根拠 N]`, `[근거 1, 3]` 형태를 찾아 등장 순서·중복 제거
- `select_cited(evidence, text) -> list[Evidence]`: 존재하는 번호만, 번호순
- `preview(ev, max_lines) -> str`: 가사 근거는 `quote_lines` 로 `display.lyrics_quote_max_lines` 줄 제한, 다른 근거는 앞 200자

### 3.5 그래프 (`rag/graph.py`)
```python
class RagState(TypedDict, total=False):
    song_id: str; question: str; history: list[tuple[str, str]]
    evidence: list[Evidence]; answer: Answer

def build_graph(store, chat, settings) -> CompiledStateGraph   # START → retrieve → generate → END
def graph_nodes(graph) -> set[str]                               # __start__/__end__ 제외 노드 이름
```

## 4. 수용 기준 (AC)
| 테스트 ID | 조건 | 기대 결과 |
|-----------|------|-----------|
| T-F2007-1 | 컴파일된 그래프 | 노드가 정확히 `retrieve`, `generate` |
| T-F2007-2 | 프롬프트의 근거 블록 | 근거마다 `[근거 N] (유형) 제목` 머리말 |
| T-F2007-3 | 근거 0개 | LLM 미호출, "확인되지 않습니다" 응답, `no_citation=True` |
| T-F2007-4 | 시스템 프롬프트 | 근거 외 사용 금지·질문 언어·인용 줄 제한·확인 불가 문구 규칙 포함 |
| T-F2007-5 | 언어 판별 | 한국어/일본어/영어 문장을 각각 ko/ja/en |
| T-F2007-6 | 그래프 실행 | 상태에 evidence·answer 가 채워짐 |
| T-F2007-7 | 영어/일본어/한국어 질문 | 프롬프트(시스템·사람)에 `English`/`日本語`/`한국어` 답변 언어 명시 |
| T-F2008-1 | 본문에 `[근거 1]`, `[근거 3]` | 표시 목록 1·3번 |
| T-F2008-2 | `[근거 9]` (없음) | 무시 |
| T-F2008-3 | 인용 없음 | `no_citation=True` |
| T-F2008-4 | 가사 근거 미리보기 | 설정 줄 수 이하 + `…` |
| T-F2008-5 | `[Source 2]`, `[根拠 2]`, `[근거 1, 3]` | 모두 인식 |

## 5. 테스트 계획
- `tests/test_language.py`, `tests/test_citations.py`, `tests/test_generate.py`, `tests/test_graph.py`
- 대역: `FakeChatModel`, `FakeEmbeddings`, 실제 Chroma(`tmp_path`)

## 6. 결정 필요 사항
- 없음
