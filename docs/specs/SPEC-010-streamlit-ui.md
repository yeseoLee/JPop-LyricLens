# SPEC-010 Streamlit UI·진행 상태·안내

- 상태: 완료
- 이슈: #10
- 구분: MVP
- 대응 요구사항: F2009, F2012, NF2004 (F2010·F2011 화면 연결 포함)
- 관련 절: `docs/SPEC.md` §F2009, §F2012, §6

## 1. 목적
지금까지 만든 기능을 하나의 화면으로 묶는다: 곡 선택 → 채팅(근거 표시), 조건 탐색, 구절 해석, 구절로 곡 찾기. 진행 상태와 오류 안내를 표시하고 내부 정보는 노출하지 않는다.

## 2. 범위
- 포함: `ui/messages.py`, `ui/state.py`, `ui/env.py`, `ui/service.py`, `ui/app.py`, 실행 명령 `streamlit run src/lyriclens/ui/app.py`
- 제외: HTML/JS 프론트엔드(확장 X-03)

## 3. 상세 설계

### 3.1 화면 구성 (`ui/app.py`)
- **사이드바**: 곡 선택(`제목 — 아티스트 (연도)`, 제목순, 검색 가능한 selectbox), 색인 건수(`song_meta N곡`), 선택 곡의 아티스트·타이업·utaten 원문 링크, 상시 안내(가사 저작권·번역 참고용)
- **탭 1 채팅** (F2009): 곡별 대화 기록. 질문하면 `st.status` 안에서 단계 표시 → 답변 → "답변에 사용한 근거 N건" 펼침(`[근거 N] 제목 · 유형 · 원문 링크` + 미리보기). 인용이 없으면 안내(F2008)
- **탭 2 조건 탐색** (F2011): 조건 입력 → 카드(제목·아티스트·연도·이유) → "이 곡으로 대화하기" 버튼이 선택 곡을 바꾸고 채팅 탭 안내
- **탭 3 구절 해석** (F2010-a): 선택 곡의 연 목록에서 고르거나 붙여 넣기, 번역 언어(한국어/English) → 원문(줄 제한)·참고용 번역·풀이·배경·근거
- **탭 4 구절로 곡 찾기** (F2010-b): 입력 → 카드(곡·일치 구절 2줄·원문 링크) → "이 곡으로 대화하기"

### 3.2 화면 상태 (`ui/state.py`)
```python
class ChatStore:            # session_state 에 들어가는 곡별 대화 기록
    def messages(self, song_id) -> list[dict]          # {"role", "content", "citations", "no_citation"}
    def add(self, song_id, role, content, **extra)
    def history(self, song_id, limit=4) -> list[tuple[str, str]]
def song_label(song_meta: dict) -> str                # "제목 — 아티스트 (연도)"
def song_options(metas: list[dict]) -> list[tuple[str, str]]   # (label, song_id), 제목순
```

### 3.3 환경 점검 (`ui/env.py`, F2012)
```python
def check_environment(settings, meta_count: int) -> EnvStatus   # .status: "missing_key" | "no_index" | "ok"
                                                                 # .warnings: ["missing_contact"] 등
```
- `GMS_KEY` 없음 → `missing_key`: 설정 안내 후 기능 비활성화
- `song_meta` 0건 → `no_index`: `python scripts/crawl_songs.py` → `python scripts/index_songs.py` 실행 안내
- `WIKI_CONTACT` 없음 → 경고만 (위키 호출 예절 안내)

### 3.4 서비스 계층 (`ui/service.py`)
```python
class LyricLensService:
    def __init__(self, settings, store, chat, wiki, cache): ...
    def ask(self, song_id, question, history, on_step=lambda step, detail: None) -> AskResult
        # AskResult: answer(Answer), collect(IndexedCollectResult), evidence
    def condition_search(self, condition) / interpret(...) / phrase_search(...)
```
- `ask` 단계 콜백 순서: `"queries"`(검색어 추출) → `"collect"`(후보 선별·본문 수집, 캐시 사용 건수) → `"index"`(색인 청크 수) → `"answer"`(답변 생성). 화면은 이 콜백으로 `st.status` 를 갱신
- 곡 정보(`SongInfo`)는 `song_meta` 메타데이터로 만든다 (UI는 도메인 파일을 직접 읽지 않음)
- 위키 수집 중 오류(`FetchError`)는 답변을 막지 않는다: 경고 단계 `"collect_failed"` 후 기존 근거로 답변

### 3.5 오류·내부 정보 (NF2004)
- 화면 문구는 `ui/messages.py` 에만 둔다
- 모든 서비스 호출은 `try/except Exception` 으로 감싸 `messages.GENERIC_ERROR` 만 보여주고, 상세는 `logging`(파일 `data/logs/app.log`)으로
- `st.exception`, 트레이스백 출력, 프롬프트 전문 출력 금지

### 3.6 가사 노출 제한 (D-02)
- 화면에 보이는 가사 원문은 모두 `citations.preview` / `quote_lines` 를 거쳐 `display.lyrics_quote_max_lines` 줄 이하로 제한한다. 구절 해석 탭의 연 선택 목록은 각 연의 첫 줄만 보여 준다.
- 근거 펼침의 가사 근거도 미리보기만 보여 주고 utaten 원문 링크를 붙인다.

## 4. 수용 기준 (AC)
| 테스트 ID | 조건 | 기대 결과 |
|-----------|------|-----------|
| T-F2009-1 | 곡 A·B에 메시지 추가 | 서로 섞이지 않음, history는 최근 4개 |
| T-F2009-2 | 곡 옵션 | `제목 — 아티스트 (연도)`, 제목순 |
| T-F2012-1 | 환경 점검 | 키 없음 / 색인 0건 / 정상 구분, 연락처 없음은 경고 |
| T-F2012-2 | 화면 문구·코드 검사 | messages에 키·트레이스백 없음, app.py에 `st.exception`·`traceback` 없음 |
| T-F2012-3 | `ask` 진행 콜백 | queries → collect → index → answer 순서, 결과에 답변·수집 결과 |
| T-F2012-4 | 위키 수집 실패 | `collect_failed` 단계 후에도 답변 반환 |
| T-F2012-6 | 연 선택 목록 라벨 | 각 연의 첫 줄만 |
| T-F2012-5 | 앱 실행(키 없음) | `AppTest` 로 앱을 띄우면 키 설정 안내가 보이고 예외 없음 |

## 5. 테스트 계획
- `tests/test_ui_state.py`, `tests/test_ui_env.py`, `tests/test_ui_service.py`, `tests/test_ui_app.py`(streamlit `AppTest`)
- 대역: `FakeChatModel`, `FakeEmbeddings`, `FakeWikiClient`

## 6. 결정 필요 사항
- 화면 문구 언어: MVP는 한국어 고정(답변은 질문 언어). 다국어 화면은 확장 X-05.
