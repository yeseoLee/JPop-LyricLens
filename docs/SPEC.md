# JPop LyricLens — 서비스 SPEC (v0.1)

> 일본어 가사를 한국어·영어·일본어로 검색하고, 근거와 함께 해석해 주는 RAG 기반 지식 서비스
>
> - 상위 문서: `prd.pdf` (AI 코어 프로젝트 2회차 명세서, 이하 PRD)
> - 이 문서는 **MVP 범위(PRD F2001~F2012, NF2001~NF2007)** 와 **확장 범위**를 정의한다.
> - MVP의 모든 기능 SPEC은 PRD 요구사항 번호와 1:1 이상 대응해야 한다. 확장 SPEC은 PRD와 무관하게 추가할 수 있다.
> - 기능을 추가·변경할 때는 코드보다 먼저 이 문서 또는 `docs/specs/SPEC-XXX-*.md` 를 갱신한다. (`AGENTS.md` 참고)

---

## 0. 의사결정 기록

| ID | 항목 | 결정 | 근거 |
|----|------|------|------|
| D-01 | 항목(곡) 수집 범위 | **지정 아티스트 목록** 기반 수집 (40명 × 6곡 ≈ 240곡) | 위키백과 문서가 있는 아티스트를 골라 근거 확보가 쉬움 |
| D-02 | 가사 노출 범위 | **부분 인용 + utaten 원문 링크**. 색인·검색에는 전체 가사 사용 | 가사 저작권 보호. 화면에는 필요한 몇 줄만 인용 |
| D-03 | 외부 문서 출처 | **한국어 위키백과만** (MediaWiki API) | PRD 권장안. 이용 조건(CC BY-SA 4.0) 명확 |
| D-04 | 도메인 특화 기능 | **가사 구절 해석**, **구절로 곡 찾기** | 다국어 사용자가 가장 자주 하는 두 가지 행동 |
| D-05 | 아티스트 목록 | 초안을 `config/artists.yaml` 로 관리 (부록 A) | 설정으로 분리해 나중에 바꿀 수 있게 함 |
| D-06 | UI | MVP는 **Streamlit**, F2013(HTML/CSS/JS + FastAPI)은 확장 단계 | PRD 기본 스택 |
| D-07 | 심화 기능 | **F2014 MMR**, **F2015 RAG 전후 비교** 를 확장 계획에 넣음 | F2013, F2016은 보류 |
| D-08 | 리뷰 방식 | CI 통과 후 **로컬 Claude Code 리뷰 서브에이전트**(`.claude/agents/reviewer.md`)가 PR에 리뷰 코멘트 작성 | 추가 시크릿 불필요 |
| D-09 | 크롤링 허용 | utaten `robots.txt`(`/manage`, `/outsourcing` 외 허용)와 별도 안내로 크롤링 가능함을 사용자가 확인함 (2026-10-21) | NF2007 |
| D-10 | LLM / 임베딩 | SSAFY GMS(OpenAI 호환) — 채팅 `gpt-5.4-nano`, 임베딩 `text-embedding-3-small` (설정으로 변경 가능) | 실습 환경과 동일. 임베딩은 다국어 지원 |

---

## 1. 도메인 확정 (PRD 2.1)

### 1.1 도메인
**J-POP 가사.** 항목 = 곡 1개.

### 1.2 도메인 선택 조건 충족 근거

| 조건 | 충족 내용 |
|------|-----------|
| 항목 메타데이터 약 100건 이상 | utaten.com에서 아티스트 40명 × 6곡 = **약 240곡**. 곡마다 제목, 읽기(가나), 아티스트, 작사, 작곡, 편곡, 발매일, 타이업, 가사(후리가나·로마자 포함) 속성을 가짐 |
| 외부 문서 출처 | 한국어 위키백과 (곡·아티스트·타이업 작품 문서). 이용 조건: CC BY-SA 4.0, API 사용 시 User-Agent에 연락처 포함 |
| 근거가 필요한 질문 (3개 이상) | 아래 1.3 |
| 위험 도메인 여부 | 건강·금융 같은 위험 도메인이 **아니다**. 면책 문구 대신 **가사 저작권 안내**("가사 전문은 원문 사이트에서 확인하세요")와 **번역은 참고용** 안내를 표시한다 |

### 1.3 근거 없이 답하면 틀리기 쉬운 질문 예시
1. "米津玄師의 「Lemon」은 어떤 드라마의 주제가이고, 가사의 '苦いレモンの匂い'는 무엇을 뜻하나요?" — 타이업 정보와 가사 원문이 있어야 답할 수 있다.
2. "YOASOBI 「夜に駆ける」의 원작 소설은 무엇인가요?" — LLM이 원작 제목을 지어내기 쉽다.
3. "Ado 「うっせぇわ」의 작사·작곡가는 누구인가요?" — 크레딧은 추측하면 틀린다.
4. "'君の名前を呼んだ' 같은 가사가 나오는 곡을 찾아줘" (한국어/영어 입력) — 실제 가사 색인이 없으면 곡을 지어낸다.

### 1.4 출처와 이용 조건 (NF2007)

| 출처 | 용도 | 이용 조건 / 지키는 규칙 |
|------|------|------------------|
| utaten.com | 곡 메타데이터, 가사 | robots.txt 준수, 호출 간격 3초 이상, 원본 HTML·가사 데이터는 **저장소에 커밋하지 않음**, 화면에는 부분 인용과 원문 링크만 제공 |
| 한국어 위키백과 | 외부 설명 문서 | CC BY-SA 4.0. 근거에 문서 제목과 원문 URL 표시. User-Agent에 `WIKI_CONTACT` 포함 |

이 표는 `README.md` 의 "데이터 출처" 절에도 그대로 옮긴다.

---

## 2. 시스템 개요

### 2.1 아키텍처

```
[utaten.com] --(crawl)--> data/songs.jsonl --(item text)--> [Chroma: song_meta]
                                              \--(stanza split)--> [Chroma: song_lyrics]
[사용자 질문] -> 프롬프트1(검색어 추출) -> [ko.wikipedia API] -> 프롬프트2(후보 선별)
            -> 본문 수집 -> 청킹 -> [Chroma: wiki_docs]

LangGraph:  START -> retrieve(song_meta 고정 + wiki_docs 검색 + 병합/중복 제거) -> generate(프롬프트3) -> END
UI(Streamlit): 곡 선택 / 채팅 / 조건 탐색 / 구절 해석 / 구절로 곡 찾기 / 진행 상태·안내
```

### 2.2 디렉터리 구조 (NF2005)

도메인(J-POP·utaten)에 묶인 코드는 `domain/` 아래에만 둔다.

```
src/lyriclens/
  config.py            # settings.yaml + 환경변수 로드
  llm.py               # ChatOpenAI / OpenAIEmbeddings 생성 (GMS)
  domain/              # 데이터 준비 영역 (도메인 의존)
    utaten_client.py   # HTTP 수집 (간격·재시도·UA)
    utaten_parser.py   # HTML -> Song
    models.py          # Song, LyricStanza
    item_text.py       # Song -> 색인 텍스트
    lyrics.py          # 가사 정규화, 연(stanza) 분할, 인용 길이 제한
  collect/             # 외부 문서 수집 영역
    wikipedia.py       # ko.wikipedia API 클라이언트
    query_extractor.py # 프롬프트1
    candidate_selector.py # 프롬프트2
    cache.py           # 수집 캐시 (NF2002)
  index/               # Vector Store 영역
    store.py           # Chroma 컬렉션 생성·조회·count
    chunking.py        # 청크 분할, 청크 ID 규칙
  rag/                 # RAG 파이프라인 영역
    prompts.py         # 프롬프트 1·2·3 + 특화 기능 프롬프트
    retrieve.py        # 검색·병합·중복 제거
    generate.py        # 답변 생성
    citations.py       # [근거 N] 파싱, 인용 근거만 추리기
    graph.py           # LangGraph(retrieve -> generate)
  services/            # 서비스 기능 영역
    condition_search.py # F2011
    phrase_interpret.py # F2010-a
    phrase_search.py    # F2010-b
  ui/
    app.py             # Streamlit
    messages.py        # 화면 안내 문구
scripts/
  crawl_songs.py       # utaten 수집 -> data/songs.jsonl
  index_songs.py       # song_meta, song_lyrics 색인
config/
  settings.yaml        # 청킹·검색·모델·호출 간격 설정
  artists.yaml         # 수집 대상 아티스트
tests/                 # pytest (외부 호출은 모두 대역 사용)
data/                  # (gitignore) 원본 HTML 캐시, songs.jsonl, chroma/
```

### 2.3 기술 스택
PRD 1.2-5)의 고정 버전을 그대로 쓴다 (`requirements.txt`). PRD 목록 외 추가 패키지:

| 패키지 | 이유 |
|--------|------|
| `beautifulsoup4`, `lxml` | utaten HTML 파싱 |
| `pyyaml` | 설정 파일 |
| `pytest`, `pytest-cov`, `ruff` (`requirements-dev.txt`) | TDD, CI |

---

## 3. 데이터 모델

### 3.1 Song (`data/songs.jsonl` 한 줄)

| 필드 | 타입 | 예시 | 비고 |
|------|------|------|------|
| `song_id` | str | `ut_mi26100826` | `ut_` + utaten 가사 ID. 청크 ID로도 사용 |
| `title` | str | `Lemon` | |
| `title_kana` | str \| null | `れもん` | |
| `artist` | str | `米津玄師` | |
| `artist_ko` | str \| null | `요네즈 켄시` | `artists.yaml` 에서 가져옴 |
| `lyricist` / `composer` / `arranger` | str \| null | | |
| `release_date` | str \| null | `2018-03-14` | ISO 형식으로 정규화 |
| `tieup` | str \| null | | utaten에 구조화된 정보가 없어 MVP에서는 null (SPEC-002 §3.2). 위키백과로 보완 |
| `lyrics` | str | | 루비 제거한 원문 (줄바꿈 유지) |
| `lyrics_kana` | str | | 후리가나를 적용한 히라가나 읽기 |
| `lyrics_romaji` | str \| null | | |
| `url` | str | `https://utaten.com/lyric/mi26100826/` | 원문 출처 |
| `crawled_at` | str | ISO 8601 | |

### 3.2 Vector DB 컬렉션 (PRD 2.3)

| 컬렉션 | 내용 | 청크 단위 | 청크 ID 규칙 |
|--------|------|-----------|--------------|
| `song_meta` | 곡 1개 = 색인 텍스트 1개 (F2001·F2002) | 곡당 1청크 | `{song_id}` (재색인 시 덮어쓰기) |
| `wiki_docs` | 위키백과 문서 청크 (F2005) | `chunk_size`/`chunk_overlap` | `{song_id}:{wiki_page_id}:{seq}` |
| `song_lyrics` | 가사 연(stanza) 청크 (F2010 특화 기능용) | 빈 줄 기준 연, 최대 `lyrics_chunk_lines` 줄 | `{song_id}:L{seq}` |

**메타데이터 필드**

- `song_meta`: `song_id, title, artist, artist_ko, lyricist, composer, release_date, release_year(int), tieup, url, source_type="song_meta"`
- `wiki_docs`: `song_id, song_title, doc_title, doc_id(page_id), url, query, is_primary(bool, 곡·아티스트 자체 문서 여부), collected_at, source_type="wikipedia"`
- `song_lyrics`: `song_id, title, artist, stanza_seq, url, source_type="lyrics"`

`song_id` 는 `wiki_docs` 검색 범위를 선택한 곡으로 좁히는 필터다. 빠지면 다른 곡의 문서가 근거에 섞이므로 필수 필드로 검증한다.

### 3.3 항목 텍스트 (PRD 2.2, F2001)

사용자가 곡을 찾는 기준(제목·읽기·아티스트 한/일 표기·크레딧·연도·타이업·가사 내용)을 모두 담는다.

```
제목: {title} ({title_kana})
아티스트: {artist} / {artist_ko}
작사: {lyricist} / 작곡: {composer} / 편곡: {arranger}
발매일: {release_date}
타이업: {tieup}
가사:
{lyrics}
```

- 값이 없는 줄은 생략한다.
- 가사를 넣었기 때문에 "비 오는 날 이별을 노래한 곡" 같은 조건 검색과 한국어·영어 질의의 교차 언어 검색이 가능하다.
- 텍스트가 `item_text_max_chars`(기본 6,000자)를 넘으면 가사 끝부분을 자른다.

---

## 4. 설정 (`config/settings.yaml`, PRD 2.5)

```yaml
llm:
  base_url: https://gms.ssafy.io/gmsapi/api.openai.com/v1/
  chat_model: gpt-5.4-nano
  embedding_model: text-embedding-3-small
  temperature: 0
chunking:
  chunk_size: 1000        # 위키 청크 크기(자)
  chunk_overlap: 200
  lyrics_chunk_lines: 8   # 가사 연 청크 최대 줄 수
  item_text_max_chars: 6000
retrieval:
  wiki_top_k: 5           # 외부 문서 청크 수
  lyrics_top_k: 3         # 질문과 관련된 가사 연 청크 수
  search_type: similarity # similarity | mmr (F2014 확장)
  mmr_fetch_k: 20
  condition_candidates: 20 # 조건 탐색 후보 수
  phrase_search_top_k: 10
collect:
  max_queries: 4          # 프롬프트1이 뽑을 최대 검색어 수
  candidates_per_query: 5
  min_doc_chars: 200      # 너무 짧은 문서 제외 (곡 자체 문서는 예외)
  request_interval_sec: 1.0 # 위키백과 호출 간격
  max_retries: 3
crawl:
  request_interval_sec: 3.0
  max_retries: 3
  songs_per_artist: 6
display:
  lyrics_quote_max_lines: 4   # 화면에 인용할 가사 최대 줄 수 (D-02)
paths:
  songs: data/songs.jsonl
  raw_html: data/raw
  chroma: data/chroma
  collect_cache: data/cache/collected.json
  docs_bundle: data/docs_bundle
  artists: config/artists.yaml
```

환경변수(`.env`, NF2003): `GMS_KEY`(필수), `WIKI_CONTACT`(필수), `LYRICLENS_SETTINGS`(선택, 다른 설정 파일 경로). 키는 코드·로그·화면에 출력하지 않는다.

---

## 5. 기능 SPEC — MVP

각 항목의 **수용 기준(AC)** 은 그대로 테스트 케이스가 된다. 테스트 ID는 `T-F20xx-n`.
외부 호출(utaten, 위키백과, LLM, 임베딩)은 단위 테스트에서 모두 대역(fake)으로 바꾼다. 실제 호출 테스트는 `@pytest.mark.live` 로 표시하고 CI에서 제외한다.

### F2001 항목 메타데이터 적재
- **내용**: `artists.yaml` 의 아티스트별로 utaten 아티스트 페이지에서 곡 목록 상위 `songs_per_artist`곡을 수집하고, 가사 페이지를 파싱해 `Song` 으로 저장한다. `Song` 1건을 항목 텍스트(3.3) 1개로 만든다.
- **utaten 파싱 규칙**
  - 제목: `.newLyricTitle__main`, 읽기: `.newLyricTitle__kana`
  - 크레딧·발매일: `.newLyricWork` 안의 `作詞/作曲/編曲` 항목, `.newLyricWork__date`
  - 가사: `.hiragana` 블록. `<span class="rb">` 는 원문, `<span class="rt">` 는 읽기. 원문 가사는 `rt` 를 버리고, 읽기 가사는 `rb` 를 `rt` 로 바꿔 만든다.
  - 로마자: `.romaji` 블록
  - 선택자는 `utaten_parser.py` 상수로 모아 사이트 구조 변경 시 한 곳만 고친다.
- **AC**
  - T-F2001-1: 픽스처 HTML을 파싱하면 제목·아티스트·작사·작곡·발매일·가사·URL이 채워진 `Song` 이 나온다.
  - T-F2001-2: 루비가 있는 줄에서 원문 가사에는 `rt` 텍스트가 없고, 읽기 가사에는 `rb` 대신 `rt` 가 들어간다.
  - T-F2001-3: 항목 텍스트에 3.3의 속성이 모두 들어가고, 값이 없는 속성의 줄은 빠진다.
  - T-F2001-4: 수집 스크립트는 `songs.jsonl` 의 곡 수를 출력하고, 최종 곡 수가 100건 미만이면 경고한다.
  - T-F2001-5: 같은 `song_id` 는 한 번만 저장된다.
- **테스트 픽스처 주의**: 실제 가사를 저장소에 넣지 않는다. utaten과 같은 HTML 구조에 **직접 지은 가사**를 넣은 합성 픽스처를 쓴다.

### F2002 메타데이터 색인 (RAG 1)
- **내용**: 항목 텍스트를 임베딩해 `song_meta` 에 곡당 1청크로 넣는다. 청크 ID = `song_id`. 같은 스크립트에서 `song_lyrics` 도 색인한다.
- **AC**
  - T-F2002-1: N곡을 색인하면 `song_meta` count = N.
  - T-F2002-2: 색인을 두 번 실행해도 count가 그대로다 (upsert).
  - T-F2002-3: 색인 스크립트는 색인한 청크 수를 출력한다.
  - T-F2002-4: 저장된 메타데이터에 3.2의 필수 필드가 있다.

### F2003 검색어 추출 (프롬프트 1)
- **내용**: "J-POP 음악 평론가이자 일본 대중문화 전문가" 역할로 곡 정보와 질문을 받아 한국어 위키백과 검색어를 **JSON 배열**로 받는다.
- **규칙**
  - 곡 제목과 아티스트명(한국어 표기 우선)은 LLM 결과와 관계없이 항상 검색어 맨 앞에 넣는다 (곡 자체 문서 보장).
  - 최대 `max_queries`개. 중복 검색어는 제거한다.
  - JSON 파싱에 실패하면 한 번 다시 요청하고, 그래도 실패하면 기본 검색어(곡 제목·아티스트)만 쓴다.
- **AC**
  - T-F2003-1: LLM이 `["드라마 언내추럴"]` 을 주면 결과는 `[곡 제목, 아티스트, "드라마 언내추럴"]`.
  - T-F2003-2: 코드블록(```json)으로 감싼 응답도 파싱한다.
  - T-F2003-3: 파싱 불가 응답이면 기본 검색어만 반환하고 예외를 던지지 않는다.
  - T-F2003-4: 결과 개수는 `max_queries` + 기본 검색어 수를 넘지 않는다.

### F2004 외부 문서 수집 (프롬프트 2)
- **내용**: 검색어마다 위키백과 `list=search` 로 후보(제목·요약)를 모으고, 프롬프트 2가 후보 중 색인할 문서의 **page_id 배열(JSON)** 을 고른다. 고른 문서만 `prop=extracts&explaintext` 로 본문을 받는다.
- **규칙**
  - "곡 자체 문서"(제목이 곡 제목과 일치하는 문서)와 "아티스트 문서"는 `is_primary=true` 로 표시하고, 선별·`min_doc_chars` 같은 제외 규칙보다 우선해 항상 수집한다. 곡 문서가 위키백과에 없으면 아티스트 문서가 이 역할을 대신한다.
  - 이미 수집한 `(song_id, 검색어)` 는 다시 검색하지 않는다 (NF2002, `collect/cache.py`).
  - 위키백과 호출: User-Agent `JPopLyricLens/0.1 (WIKI_CONTACT)`, 호출 간격 1초 이상, 429·5xx는 지수 백오프로 최대 3회 재시도 (NF2006).
  - 외부 호출이 막힌 환경에서는 `data/docs_bundle/*.json`(제목·URL·본문)을 읽어 수집 단계를 대신한다.
- **AC**
  - T-F2004-1: 선별 프롬프트가 고른 문서만 본문을 요청한다 (가짜 클라이언트 호출 기록으로 확인).
  - T-F2004-2: 선별 결과에 곡 자체 문서가 없어도, 그 문서가 짧아도 수집 결과에 들어간다.
  - T-F2004-3: 같은 곡·검색어로 두 번 수집하면 두 번째에는 위키백과 호출이 0회다.
  - T-F2004-4: 수집 결과마다 제목·URL·page_id·본문이 있다.
  - T-F2004-5: 모든 요청에 연락처가 든 User-Agent가 붙고, 429 응답 후 재시도한다.
  - T-F2004-6: 수집 결과에 "색인한 문서 / 버린 문서" 목록이 함께 반환된다 (검증 4.2용).

### F2005 외부 문서 색인 (RAG 2)
- **내용**: 수집한 본문을 `RecursiveCharacterTextSplitter(chunk_size, chunk_overlap)` 로 나눠 `wiki_docs` 에 색인한다.
- **AC**
  - T-F2005-1: 청크 ID가 `{song_id}:{page_id}:{seq}` 형식이다.
  - T-F2005-2: 서로 다른 두 곡이 같은 문서를 수집해도 청크가 서로 덮어쓰지 않는다.
  - T-F2005-3: `chunk_size` 를 줄이면 같은 문서의 청크 수가 늘어난다 (설정만 바꿔 확인).
  - T-F2005-4: 각 청크 메타데이터에 `doc_title, url, song_id` 가 있다.

### F2006 근거 검색 및 병합
- **내용**: `retrieve` 노드는
  1. 선택한 곡의 `song_meta` 청크를 **검색 없이 ID로** 가져와 항상 1번 근거로 넣는다.
  2. `wiki_docs` 를 `filter={"song_id": 선택 곡}` 으로 범위를 좁혀 질문과 의미 유사도로 `wiki_top_k`개 검색한다.
  3. `song_lyrics` 를 같은 필터로 `lyrics_top_k`개 검색한다.
  4. 병합 후 청크 ID 기준으로 중복을 제거하고, 같은 문서에서 본문이 같은 청크도 제거한다. 순서: 메타 → 가사 → 위키.
  5. 근거마다 1부터 번호를 붙이고 `source_type` 을 붙인다.
- **AC**
  - T-F2006-1: 질문과 상관없이 선택 곡의 메타 청크가 항상 근거 1번이다.
  - T-F2006-2: 다른 곡의 위키 청크는 근거에 들어가지 않는다.
  - T-F2006-3: 같은 청크 ID가 두 번 나오면 하나만 남는다.
  - T-F2006-4: `wiki_top_k` 를 3→6으로 바꾸면 위키 근거 수가 바뀐다 (설정만 바꿔 확인).

### F2007 근거 기반 답변 생성 (프롬프트 3)
- **내용**: LangGraph `StateGraph` 를 `retrieve` → `generate` 두 노드로 구성한다. 프롬프트 3 규칙:
  - 주어진 근거만 사용한다. 근거로 확인되지 않으면 "제공된 문서에서 확인되지 않습니다"(질문 언어로)라고 답한다.
  - 주요 주장마다 `[근거 N]` 을 붙인다.
  - **질문 언어로 답한다** (ko/en/ja). 가사를 번역할 때는 원문 한 줄과 번역을 함께 쓴다.
  - 가사 원문 인용은 한 번에 최대 `lyrics_quote_max_lines`줄 (D-02).
  - 근거 목록 표기에 출처 유형(`곡 정보` / `가사` / `위키백과`)을 붙여 전달한다.
- **AC**
  - T-F2007-1: 컴파일된 그래프의 노드가 정확히 `retrieve`, `generate` 두 개다.
  - T-F2007-2: 프롬프트에 들어간 근거 블록마다 `[근거 N] (유형) 제목` 머리말이 있다.
  - T-F2007-3: 근거가 0개(메타 청크 제외 시 등)면 LLM을 부르지 않고 "확인되지 않습니다" 응답을 반환한다.
  - T-F2007-4: 시스템 프롬프트에 근거 외 사용 금지·질문 언어 응답·인용 줄 제한 규칙이 있다 (스냅샷 테스트).

### F2008 근거 표시
- **내용**: 답변 본문에서 `[근거 N]`(영어 `[Source N]`, 일본어 `[根拠 N]` 도 허용)을 정규식으로 찾아, 실제로 인용된 근거만 `제목 · 유형 · 원문 링크` 로 표시한다.
  - 가사 근거는 화면에 `lyrics_quote_max_lines` 줄까지만 미리보기로 보여주고 utaten 링크를 붙인다.
- **AC**
  - T-F2008-1: 본문에 `[근거 1]`, `[근거 3]` 만 있으면 표시 목록은 1·3번뿐이다.
  - T-F2008-2: 존재하지 않는 번호(`[근거 9]`)는 무시한다.
  - T-F2008-3: 인용이 하나도 없으면 "답변에 인용된 근거가 없습니다" 안내 플래그를 반환한다.
  - T-F2008-4: 가사 근거 미리보기는 설정한 줄 수를 넘지 않는다.

### F2009 항목 선택 및 질의응답
- **내용**: 사이드바에서 곡을 검색·선택한다(`제목 — 아티스트 (연도)`). 대화 기록은 `st.session_state["chats"][song_id]` 에 곡별로 저장한다. 곡을 처음 질문할 때 F2003~F2005 수집을 실행하고, 그 뒤 그래프를 호출한다.
- **AC**
  - T-F2009-1: 대화 저장소(`ChatStore`)에 곡 A, B 메시지를 넣으면 서로 섞이지 않는다.
  - T-F2009-2: 곡 목록 라벨이 `제목 — 아티스트 (연도)` 형식이고 제목순으로 정렬된다.
  - UI 동작 자체는 검증 체크리스트(수동 + 스크린샷)로 확인한다.

### F2010 도메인 특화 기능
두 기능 모두 근거 번호와 근거 목록을 F2008 방식으로 함께 보여준다.

**F2010-a 가사 구절 해석**
- 선택 곡의 가사 연 목록에서 구절을 고르거나 붙여 넣으면, 해당 연 청크 + 메타 + 관련 위키 청크를 근거로 **번역(한국어·영어 중 선택) / 표현·단어 풀이 / 곡 배경과의 연결**을 생성한다.
- 근거에 없는 배경 설명은 쓰지 않는다. 번역은 "참고용 번역" 표시를 붙인다.
- AC
  - T-F2010-1: 해석 결과 구조가 `translation, notes[], background, citations[]` 이다.
  - T-F2010-2: 붙여 넣은 구절이 가사에 없으면 "이 곡의 가사에서 찾지 못했습니다"를 반환하고 LLM을 부르지 않는다.
  - T-F2010-3: 결과의 원문 인용은 설정한 줄 수를 넘지 않는다.

**F2010-b 구절로 곡 찾기 (교차 언어 검색)**
- 사용자가 기억나는 가사를 ko/en/ja 중 아무 언어로 입력하면,
  1. 입력이 일본어가 아니면 LLM으로 일본어 가사 표현 후보 1~2개로 바꾼다 (원문 질의도 함께 사용).
  2. 각 질의로 `song_lyrics` 를 검색해 곡별로 최고 점수를 모은다.
  3. 상위 곡을 카드(곡명·아티스트·일치한 구절 최대 2줄·원문 링크)로 보여주고, 카드를 누르면 그 곡의 채팅으로 이동한다.
- AC
  - T-F2010-4: 한국어 입력이면 번역 질의 + 원문 질의 두 번 검색한다.
  - T-F2010-5: 같은 곡의 여러 연이 걸리면 곡은 한 번만 나온다.
  - T-F2010-6: 결과는 `phrase_search_top_k` 이하이며 점수 내림차순이다.

### F2011 조건 기반 항목 탐색
- **내용**: "비 오는 날 듣기 좋은 이별 노래", "2020년 이후 애니 주제가" 같은 자연어 조건을 받는다.
  1. `song_meta` 에서 유사도 상위 `condition_candidates`곡을 가져온다. (연도 조건이 있으면 LLM이 뽑은 `release_year` 필터를 함께 적용)
  2. 선별 프롬프트에 후보 메타 요약을 주고, 조건에 맞는 `song_id` 와 한 줄 이유를 **JSON** 으로 받는다.
  3. 후보에 없는 `song_id` 는 버린다. 카드를 누르면 그 곡의 대화로 이어진다.
- **AC**
  - T-F2011-1: LLM이 후보에 없는 ID를 돌려주면 결과에서 빠진다.
  - T-F2011-2: LLM이 빈 배열을 주면 "조건에 맞는 곡을 찾지 못했습니다" 상태를 반환한다.
  - T-F2011-3: 연도 조건이 추출되면 Chroma 조회에 `release_year` 필터가 들어간다.

### F2012 진행 상태 및 안내
- **내용**
  - 문서 수집·답변 생성 중 `st.status` 로 단계(검색어 추출 → 후보 선별 → 본문 수집 → 색인 → 답변 생성)를 표시하고, 끝나면 수집 문서 제목을 보여준다. 캐시 사용 시 "이미 수집한 문서 N건 사용".
  - `GMS_KEY` 누락 → 설정 방법 안내 후 채팅 비활성화.
  - `song_meta` count 0 → `python scripts/index_songs.py` 실행 안내.
  - 위키 검색 결과 없음 → "외부 문서를 찾지 못해 곡 정보와 가사만으로 답합니다".
  - 상시 안내: 가사 저작권 안내 + 번역 참고용 안내 (위험 도메인 면책 대신, 1.2 참고).
- **AC**
  - T-F2012-1: `check_environment()` 가 키 없음 / 색인 0건 / 정상 세 상태를 구분해 반환한다.
  - T-F2012-2: 안내 문구는 `ui/messages.py` 에만 있고 키 값이나 예외 추적 정보를 포함하지 않는다.

---

## 6. 비기능 SPEC — MVP

| ID | 내용 | 검증 방법 |
|----|------|-----------|
| NF2001 응답 시간 | 수집 캐시가 있는 대표 질문은 답변까지 15초 이내, 첫 수집 포함 60초 이내 | 대표 질문 5개 수동 측정, 검증 문서에 기록 |
| NF2002 수집 캐시 | `(song_id, 검색어)` 단위 캐시, 이미 색인된 page_id는 다시 받지 않음 | T-F2004-3 |
| NF2003 API 키 관리 | 키는 `.env`/환경변수에서만 읽음. CI에서 `GMS_KEY=` 패턴·`sk-` 문자열 커밋 검사 | `tests/test_security.py` (저장소 파일 스캔) |
| NF2004 내부 정보 비노출 | UI는 예외를 잡아 `messages.py` 의 일반 문구만 보여주고, 상세는 로그 파일로. 프롬프트 전문을 화면에 출력하지 않음 | T-F2012-2, 코드 리뷰 |
| NF2005 모듈 분리 | 2.2 구조. `collect/ index/ rag/ services/` 는 `domain/` 외에는 utaten을 import하지 않음 | `tests/test_architecture.py` (import 검사) |
| NF2006 외부 API 예절 | utaten 3초·위키 1초 간격, 지수 백오프 3회, UA 연락처 | T-F2004-5, `utaten_client` 테스트 |
| NF2007 출처와 이용 조건 | 1.4 표를 README에 기록, 원본 가사 데이터 비커밋(`.gitignore`) | `test_security.py` 에서 `data/` 추적 여부 검사 |

---

## 7. 테스트 전략

- **TDD**: 이슈 SPEC의 AC → 실패하는 테스트 작성(커밋) → 구현 → 통과.
- **대역**: `tests/fakes.py` 에 `FakeChatModel`(정해진 응답 반환·호출 기록), `FakeEmbeddings`(해시 기반 결정적 벡터), `FakeWikiClient`, 합성 utaten HTML 픽스처.
- **Chroma**: 테스트마다 `tmp_path` 의 임시 경로를 쓰는 실제 Chroma를 사용한다.
- **마커**: `live`(실제 네트워크·LLM) — CI 제외, 로컬에서 `pytest -m live`.
- **CI** (`.github/workflows/ci.yml`): Python 3.12, `ruff check`, `pytest -m "not live" --cov=lyriclens`.
- **추적성**: 테스트 함수 docstring 첫 줄에 테스트 ID(`T-F2006-1`)를 쓴다. `docs/verification.md` 의 요구사항 대조표가 이 ID를 참조한다.

---

## 8. 작업 분해 (MVP 이슈 계획)

| 순서 | 이슈 | 대응 요구사항 |
|------|------|---------------|
| 1 | 프로젝트 골격·설정 로더·CI·보안/구조 테스트 | NF2003, NF2005, NF2007 |
| 2 | utaten 클라이언트·파서·수집 스크립트 | F2001, NF2006, NF2007 |
| 3 | 항목 텍스트·`song_meta`/`song_lyrics` 색인 | F2001, F2002 |
| 4 | 위키백과 클라이언트·검색어 추출·후보 선별·수집 캐시 | F2003, F2004, NF2002, NF2006 |
| 5 | 위키 문서 청킹·색인 | F2005 |
| 6 | retrieve(병합·중복 제거) | F2006 |
| 7 | generate·LangGraph·근거 파싱/표시 | F2007, F2008 |
| 8 | 조건 기반 탐색 | F2011 |
| 9 | 특화 기능: 구절 해석, 구절로 곡 찾기 | F2010 |
| 10 | Streamlit UI·진행 상태·안내 | F2009, F2012, NF2004 |
| 11 | 검증 문서·README·RAG 파이프라인 설계문서 | PRD 4장, 6장 |

이슈마다 `docs/specs/SPEC-XXX-<slug>.md` 를 이 문서에서 해당 절을 옮겨 상세화해 작성한다 (`docs/specs/_TEMPLATE.md`).

---

## 9. 확장 SPEC (PRD 대응 불필요)

확장 기능도 착수 전에 `docs/specs/` 에 SPEC을 먼저 작성한다.

| ID | 기능 | 요약 | 상태 |
|----|------|------|------|
| X-01 | F2014 MMR 검색 | `search_type: mmr`, `mmr_fetch_k=20` 에서 `wiki_top_k` 선별. 같은 질문의 유사도/MMR 근거 목록 비교 스크립트 `scripts/compare_retrieval.py` | 계획 |
| X-02 | F2015 RAG 전후 비교 | 대표 질문 5개 이상을 RAG 없이/있이 답하게 하고 사실 정확성·근거 제시·모름 인정 세 기준으로 `docs/rag_comparison.md` 작성 | 계획 |
| X-03 | F2013 프론트엔드 | FastAPI(`/api/songs`, `/api/chat`, `/api/search`) + HTML/CSS/JS | 보류 |
| X-04 | F2016 여러 출처 결합 | 가사 해설 블로그·PDF 등 추가 출처 | 보류 |
| X-05 | UI 다국어 | 화면 문구 ko/en/ja 전환 (`messages.py` 다국어화) | 아이디어 |
| X-06 | 노래방 읽기 가이드 | 후리가나·로마자를 한글 발음으로 표시 | 아이디어 |

---

## 부록 A. 수집 대상 아티스트 초안 (`config/artists.yaml`)

한국어 위키백과에 문서가 있는 아티스트 위주. `utaten_artist_id` 는 이슈 2에서 확인해 채운다.

| # | 아티스트 | 한국어 표기 |
|---|---|---|
| 1 | 米津玄師 | 요네즈 켄시 |
| 2 | YOASOBI | 요아소비 |
| 3 | Ado | 아도 |
| 4 | Official髭男dism | 오피셜히게단디즘 |
| 5 | Mrs. GREEN APPLE | 미세스 그린 애플 |
| 6 | King Gnu | 킹 누 |
| 7 | 優里 | 유우리 |
| 8 | imase | 이마세 |
| 9 | RADWIMPS | 래드윔프스 |
| 10 | Creepy Nuts | 크리피 넛츠 |
| 11 | あいみょん | 아이묭 |
| 12 | back number | 백 넘버 |
| 13 | 藤井風 | 후지이 카제 |
| 14 | Vaundy | 바운디 |
| 15 | ヨルシカ | 요루시카 |
| 16 | LiSA | 리사 |
| 17 | Eve | 이브 |
| 18 | Aimer | 에메 |
| 19 | tuki. | 츠키 |
| 20 | なとり | 나토리 |
| 21 | SEKAI NO OWARI | 세카이노 오와리 |
| 22 | ONE OK ROCK | 원 오크 록 |
| 23 | KANA-BOON | 카나분 |
| 24 | yama | 야마 |
| 25 | ずっと真夜中でいいのに。 | 계속 한밤중이면 좋을 텐데. |
| 26 | ロクデナシ | 로쿠데나시 |
| 27 | 美波 | 미나미 |
| 28 | 冨岡愛 | 도미오카 아이 |
| 29 | DISH// | 디쉬 |
| 30 | Tani Yuuki | 타니 유우키 |
| 31 | SPYAIR | 스파이에어 |
| 32 | 宇多田ヒカル | 우타다 히카루 |
| 33 | Saucy Dog | 사우시 독 |
| 34 | BUMP OF CHICKEN | 범프 오브 치킨 |
| 35 | サカナクション | 사카낙션 |
| 36 | X JAPAN | 엑스 재팬 |
| 37 | milet | 미레이 |
| 38 | 『ユイカ』 | 유이카 |
| 39 | 星野源 | 호시노 겐 |
| 40 | HoneyWorks | 허니웍스 |
