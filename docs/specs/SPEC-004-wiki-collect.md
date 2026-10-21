# SPEC-004 위키백과 수집: 검색어 추출·후보 선별·수집 캐시

- 상태: 진행 중
- 이슈: #4
- 구분: MVP
- 대응 요구사항: F2003, F2004, NF2002, NF2006
- 관련 절: `docs/SPEC.md` §F2003, §F2004, §6

## 1. 목적
선택한 곡과 질문에 맞는 한국어 위키백과 문서를 골라 본문과 원문 URL을 수집한다. 색인은 SPEC-005에서 한다.

## 2. 범위
- 포함: `collect/wikipedia.py`(API 클라이언트, 오프라인 묶음 클라이언트), `collect/query_extractor.py`(프롬프트 1), `collect/candidate_selector.py`(프롬프트 2), `collect/cache.py`, `collect/collector.py`(수집 흐름), `rag/prompts.py`(프롬프트 1·2), `jsonparse.py`
- 제외: 청킹·색인(SPEC-005), UI 진행 표시(SPEC-010)

## 3. 상세 설계

### 3.1 데이터 형식
```python
@dataclass
class SongInfo:            # collect/ 는 도메인 모델(Song)을 모른다 (NF2005)
    song_id: str; title: str; artist: str; artist_ko: str | None = None; tieup: str | None = None

@dataclass
class WikiCandidate:  page_id: int; title: str; snippet: str
@dataclass
class WikiPage:       page_id: int; title: str; url: str; text: str
@dataclass
class CollectedDoc:   page: WikiPage; query: str; is_primary: bool

@dataclass
class CollectResult:
    queries: list[str]
    indexed: list[CollectedDoc]        # 새로 수집해 색인할 문서
    discarded: list[WikiCandidate]     # 선별에서 버린 후보 (검증 4.2)
    cached_queries: list[str]          # 캐시 때문에 건너뛴 검색어
```

### 3.2 위키백과 클라이언트 (`WikiClient`, NF2006)
- 엔드포인트 `https://ko.wikipedia.org/w/api.php`, `format=json`, `formatversion=2`
- `search(query, limit) -> list[WikiCandidate]`: `list=search`. snippet의 HTML 태그 제거
- `find_page(title) -> WikiCandidate | None`: `titles=<title>&redirects=1`. 문서가 없으면 None
- `fetch(page_id) -> WikiPage`: `prop=extracts|info&explaintext=1&inprop=url&pageids=<id>`
- User-Agent `JPopLyricLens/0.1 (+mailto:<WIKI_CONTACT>)`, 호출 간격 `collect.request_interval_sec`(1초), 429·5xx·연결 오류는 지수 백오프로 `collect.max_retries` 회 재시도. 연락처가 없으면 경고 로그
- `BundleWikiClient(dir)`: `data/docs_bundle/*.json`(`{page_id,title,url,text}`)으로 같은 인터페이스 제공. `search` 는 제목·본문에 검색어가 들어간 문서, snippet은 본문 앞 200자. 외부 호출이 막힌 환경용 (F2004)

### 3.3 프롬프트 1 — 검색어 추출 (`extract_queries(song, question, chat, max_queries)`)
- 시스템: "너는 J-POP 음악 평론가이자 일본 대중문화 전문가다" + 한국어 위키백과에서 찾을 검색어를 **JSON 문자열 배열만** 출력하라는 규칙
- 사람 메시지: 곡 제목·아티스트·타이업·질문
- 결과 = 기본 검색어 `[title, artist_ko or artist]` + LLM 검색어(최대 `max_queries`), 공백 정리 후 중복 제거
- 파싱 실패 시 1회 재요청, 그래도 실패하면 기본 검색어만

### 3.4 프롬프트 2 — 후보 선별 (`select_candidates(song, question, candidates, chat) -> set[int]`)
- 후보의 page_id·제목·요약만 보여 주고 색인할 page_id를 **JSON 정수 배열만** 출력
- 후보에 없는 ID는 버림. 파싱 실패 시 1회 재요청, 그래도 실패하면 빈 집합(1차 문서만 수집)

### 3.5 수집 흐름 (`collect_documents(song, question, chat, wiki, cache, settings)`)
1. 검색어 추출 → 캐시에 있는 `(song_id, 검색어)` 는 `cached_queries` 로 빼고 검색하지 않음 (NF2002)
2. 1차 문서: 곡 문서(`find_page(title)` 또는 검색 결과 중 제목이 곡 제목과 같거나 `곡 제목 (` 로 시작) + 아티스트 문서(`find_page(artist_ko or artist)`). 곡 문서가 없으면 아티스트 문서가 그 역할을 한다. 1차 문서는 캐시·선별·`min_doc_chars` 와 관계없이 아직 수집하지 않았다면 항상 수집 (`is_primary=True`)
3. 남은 검색어로 `search(q, candidates_per_query)` → 1차 문서·이미 수집한 page_id 를 뺀 후보 → 선별 → 고른 문서만 `fetch`
4. `min_doc_chars` 미만인 2차 문서는 버린다
5. 검색어와 수집한 page_id 를 캐시에 기록 (`data/cache/collected.json`: `{song_id: {"queries": [...], "page_ids": [...]}}`)

## 4. 수용 기준 (AC)
| 테스트 ID | 조건 | 기대 결과 |
|-----------|------|-----------|
| T-F2003-1 | LLM이 `["드라마 언내추럴"]` | `[곡 제목, 아티스트, "드라마 언내추럴"]` |
| T-F2003-2 | ```json 코드블록 응답 | 파싱 성공 |
| T-F2003-3 | 두 번 모두 파싱 불가 | 기본 검색어만, 예외 없음, LLM 2회 호출 |
| T-F2003-4 | LLM이 검색어 10개 | 기본 2개 + `max_queries` 개 이하 |
| T-F2004-1 | 선별이 후보 일부만 고름 | 고른 문서만 fetch |
| T-F2004-2 | 곡 문서가 선별에서 빠지고 짧음 | 그래도 `is_primary=True` 로 수집 |
| T-F2004-3 | 같은 곡·질문 두 번 수집 | 두 번째 위키 search/fetch 0회 |
| T-F2004-4 | 수집 결과 | 각 문서에 제목·URL·page_id·본문 |
| T-F2004-5 | WikiClient 요청 | UA에 연락처, 간격 ≥1초, 429 후 재시도 |
| T-F2004-6 | 수집 결과 | `discarded` 에 버린 후보 |
| T-F2004-7 | BundleWikiClient | 묶음 파일로 search/fetch/find_page 동작 |
| T-F2004-8 | 후보에 없는 ID를 선별이 반환 | 무시 |

## 5. 테스트 계획
- `tests/test_query_extractor.py`, `tests/test_candidate_selector.py`, `tests/test_wikipedia.py`, `tests/test_collector.py`
- 대역: `FakeChatModel`(응답 큐·호출 기록), `FakeWikiClient`, `FakeSession`/`FakeClock`
- live: `tests/test_wikipedia_live.py` (실제 위키 검색 1회, `WIKI_CONTACT` 필요)

## 6. 결정 필요 사항
- 없음
