# JPop LyricLens

일본어 가사를 **한국어·English·日本語** 로 검색하고, 근거 문서와 함께 해석해 주는 RAG 기반 지식 서비스입니다.

- 곡 240곡(아티스트 40명 × 인기곡 6곡)의 메타데이터와 가사를 UtaTen에서 수집해 색인합니다.
- 질문하면 한국어 위키백과에서 관련 문서를 골라 수집·색인하고, **검색된 근거만으로** 질문한 언어로 답합니다.
- 답변의 주장마다 `[근거 N]` 을 붙이고, 실제로 인용한 근거의 제목과 원문 링크를 보여 줍니다.

| 문서 | 내용 |
|------|------|
| [`docs/SPEC.md`](docs/SPEC.md) | 요구사항 정의서 (도메인 확정 근거, PRD 요구사항별 기능 SPEC, 의사결정 기록) |
| [`docs/rag_pipeline.md`](docs/rag_pipeline.md) | RAG 파이프라인 설계문서 |
| [`docs/verification.md`](docs/verification.md) | 검증 결과 (요구사항 대조표, 실행 결과, 체크리스트) |
| [`docs/specs/`](docs/specs) | 이슈별 상세 SPEC |
| [`AGENTS.md`](AGENTS.md) | 개발 흐름 (SPEC → 테스트 → 구현 → PR → CI → 리뷰 → 머지) |

## 실행 방법

Python 3.10 이상 (개발·CI는 3.12).

```bash
# 1) 설치
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2) 환경변수 — .env.example 을 복사해 값을 채운다 (.env 는 커밋하지 않음)
cp .env.example .env        # GMS_KEY, WIKI_CONTACT(연락처 이메일)

# 3) 곡 수집 (UtaTen, 3초 간격 · 약 15분, 원본 HTML은 data/raw 에 캐시)
python scripts/crawl_songs.py

# 4) 곡 색인 (song_meta 240건, song_lyrics 약 2,800건)
python scripts/index_songs.py

# 5) (권장) 곡·아티스트 위키 문서 미리 수집 — 첫 질문 시간 단축 (약 15~20분)
#    앱을 끈 상태에서 실행하세요 (앱과 같은 수집 캐시 파일을 씁니다)
python scripts/prefetch_wiki.py

# 6) 실행
streamlit run src/lyriclens/ui/app.py
```

> **모델을 바꾸면 다시 색인해야 합니다.** 임베딩 모델(`config/settings.yaml` 의 `llm.embedding_model`)이 바뀌면 벡터 차원이 달라져 기존 색인을 쓸 수 없습니다. `data/chroma` 와 `data/cache/collected.json` 을 지우거나 옮긴 뒤 4)부터 다시 실행하세요.

테스트:

```bash
pip install -r requirements-dev.txt
pytest -m "not live"      # 단위 테스트 (외부 호출 없음, CI와 동일)
pytest -m live            # 실제 UtaTen·위키백과 호출 (WIKI_CONTACT 필요)
ruff check .
```

## 기능

### 필수 기능 (PRD F2001~F2012)

| 번호 | 기능 | 화면 |
|------|------|------|
| F2001·F2002 | 곡 메타데이터 적재·색인 — 곡 1건 = 제목·읽기·아티스트(일/한)·크레딧·발매일·타이업·가사를 담은 텍스트 1개 | 사이드바 색인 건수 |
| F2003 | 검색어 추출(프롬프트 1) — J-POP 평론가 역할, JSON 배열 | 진행 상태 |
| F2004 | 위키백과 수집(프롬프트 2) — 후보 선별, 곡·아티스트 문서는 항상 수집 | 진행 상태 |
| F2005 | 위키 문서 청킹·색인 (1000자 / 200자 중복) | 진행 상태 |
| F2006 | 근거 검색·병합 — 곡 정보 고정 + 가사·위키 곡 범위 검색, 중복 제거 | — |
| F2007 | 근거 기반 답변(프롬프트 3) — LangGraph `retrieve → generate`, 질문 언어로 답변 | 💬 질문하기 |
| F2008 | 근거 표시 — 인용된 근거만, 제목·유형·원문 링크 | 답변 아래 펼침 |
| F2009 | 곡 선택·곡별 대화 기록 | 사이드바 + 💬 질문하기 |
| F2010 | 특화 기능: **가사 구절 해석**(번역·표현 풀이·배경), **구절로 곡 찾기**(ko/en/ja 입력 → 일본어 가사 검색) | 📖 구절 해석, 🎵 구절로 곡 찾기 |
| F2011 | 조건 기반 탐색 — 자연어 조건(연도 포함) → 맞는 곡만 이유와 함께 | 🔎 조건으로 찾기 |
| F2012 | 진행 상태, 키 없음·색인 없음·외부 문서 없음 안내, 저작권·번역 참고용 안내 | 전역 |

### 심화 기능 (계획)

| 번호 | 상태 |
|------|------|
| F2014 MMR 검색 | 계획 (`docs/SPEC.md` §9 X-01) |
| F2015 RAG 전후 품질 비교 | 계획 (X-02) |
| F2013 HTML/JS 프론트엔드, F2016 여러 출처 결합 | 보류 |

## 데이터 준비와 색인 절차

1. `config/artists.yaml` 의 아티스트 40명 → UtaTen 아티스트 페이지(인기순)에서 곡 6개씩 → 가사 페이지 파싱 → `data/songs.jsonl`
2. `song_meta`(곡당 1청크, ID = `song_id`)와 `song_lyrics`(가사 연 단위, `{song_id}:L{n}`)에 upsert — 다시 실행해도 건수가 늘지 않음
3. 질문 시 위키백과 문서를 수집해 `wiki_docs`(`{song_id}:{page_id}:{n}`)에 색인. 이미 수집한 (곡, 검색어)는 다시 수집하지 않음

설정값(청크 크기, Top-k, 모델, 호출 간격 등)은 모두 `config/settings.yaml` 에 있습니다.

## 출처와 이용 조건

| 출처 | 용도 | 이용 조건 / 지키는 규칙 |
|------|------|------------------|
| [UtaTen](https://utaten.com/) | 곡 메타데이터, 가사 | robots.txt 준수(`/manage`, `/outsourcing` 외 허용, 2026-10-21 확인), 별도 안내로 수집 가능함을 확인. 호출 간격 3초 이상, 연락처가 든 User-Agent. **원본 HTML·가사 데이터는 저장소에 올리지 않음**(`data/` 는 `.gitignore`). 화면에는 가사를 최대 4줄까지만 인용하고 원문 링크를 붙임 |
| [한국어 위키백과](https://ko.wikipedia.org/) | 곡·아티스트·타이업 작품 설명 | CC BY-SA 4.0. 근거마다 문서 제목과 원문 URL 표시. MediaWiki API 호출 간격 1초, User-Agent에 `WIKI_CONTACT` 연락처 포함, 429·5xx는 지수 백오프 재시도 |

가사 저작권은 각 권리자에게 있습니다. 번역과 해석은 참고용입니다.

## 기술 스택

Python · LangChain / LangGraph · ChromaDB · Streamlit · SSAFY GMS(OpenAI 호환: 답변 `gpt-6-luna`, 보조 작업 `gpt-5.4-nano`, 임베딩 `text-embedding-3-large`). 버전은 PRD 고정 버전을 따릅니다(`requirements.txt`).
