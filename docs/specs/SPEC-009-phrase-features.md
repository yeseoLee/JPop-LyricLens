# SPEC-009 특화 기능: 가사 구절 해석·구절로 곡 찾기

- 상태: 진행 중
- 이슈: #9
- 구분: MVP
- 대응 요구사항: F2010
- 관련 절: `docs/SPEC.md` §F2010

## 1. 목적
다국어 사용자가 가장 자주 하는 두 행동을 근거와 함께 지원한다.
- (a) 가사 구절의 뜻·표현·배경을 한국어/영어로 해석
- (b) 기억나는 가사를 아무 언어로 입력해 곡 찾기

## 2. 범위
- 포함: `services/phrase_interpret.py`, `services/phrase_search.py`, `rag/prompts.py`(해석·일본어 변환 프롬프트), `index/store.py` 에 `get_where` 추가
- 제외: 화면(SPEC-010)

## 3. 상세 설계

### 3.1 가사 구절 해석 (F2010-a)
```python
@dataclass
class Interpretation:
    status: str                # "ok" | "not_found"
    original: str = ""         # 화면에 보일 원문 (lyrics_quote_max_lines 줄 제한)
    translation: str = ""      # "참고용 번역" 표시는 화면에서
    notes: list[str] = ...     # 단어·표현 풀이
    background: str = ""       # 곡 배경과의 연결 ([근거 N] 포함)
    citations: list[Evidence] = ...

def interpret_phrase(song_id, phrase, target_lang, store, chat, settings) -> Interpretation
```
1. `song_lyrics` 에서 `song_id` 의 연을 모두 가져와(`get_where`) 공백을 무시하고 구절이 들어 있는 연을 찾는다. 없으면 `not_found`, LLM 미호출
2. 근거: 곡 정보(ID 조회) + 일치한 연 + `wiki_docs` 에서 구절로 검색한 `wiki_top_k` 청크, 번호 1부터
3. 해석 프롬프트(`INTERPRET_SYSTEM`): 근거만 사용, 출력 JSON `{"translation", "notes": [...], "background"}`, 번역·풀이는 `target_lang`(ko|en), 배경 설명에는 `[근거 N]`, 근거에 없는 배경은 쓰지 않음
4. `original` = 구절을 `quote_lines(lyrics_quote_max_lines)` 로 자른 것. `citations` = translation·notes·background 에서 인용된 근거
5. JSON 파싱이 끝내 실패하면 `status="ok"`, `background` 에 응답 원문, 나머지 빈 값

### 3.2 구절로 곡 찾기 (F2010-b)
```python
@dataclass
class PhraseHit:
    song_id: str; title: str; artist: str; url: str; score: float; matched: str   # 최대 2줄

def search_phrase(text, store, chat, settings) -> list[PhraseHit]
```
1. `detect_language(text) != "ja"` 이면 `PHRASE_TO_JA` 프롬프트로 일본어 가사 표현 1~2개(JSON 배열)를 받아 질의에 넣고, 원문 질의도 함께 쓴다
2. 질의마다 `song_lyrics` 를 `phrase_search_top_k * 3` 개 검색, 곡별 최고 점수만 남김
3. 점수 내림차순으로 `phrase_search_top_k` 곡. `matched` 는 최고 점수 연의 앞 2줄(`quote_lines`)

## 4. 수용 기준 (AC)
| 테스트 ID | 조건 | 기대 결과 |
|-----------|------|-----------|
| T-F2010-1 | 구절 해석 성공 | 결과에 translation·notes·background·citations, citations는 인용된 근거만 |
| T-F2010-2 | 가사에 없는 구절 | `not_found`, LLM 미호출 |
| T-F2010-3 | 긴 구절 해석 | `original` 이 설정 줄 수 이하 |
| T-F2010-4 | 한국어 입력 | 일본어 변환 질의 + 원문 질의로 검색 (LLM 1회) |
| T-F2010-5 | 한 곡의 여러 연이 걸림 | 곡은 한 번만 |
| T-F2010-6 | 결과 | `phrase_search_top_k` 이하, 점수 내림차순, matched 2줄 이하 |
| T-F2010-7 | 일본어 입력 | LLM 미호출 |
| T-F2010-8 | 해석 프롬프트 | 근거만 사용·target_lang·JSON 형식 규칙 포함 |

## 5. 테스트 계획
- `tests/test_phrase_interpret.py`, `tests/test_phrase_search.py` — `FakeChatModel`, `FakeEmbeddings`, 실제 Chroma

## 6. 결정 필요 사항
- 없음
