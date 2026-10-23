# JPop LyricLens

일본어 가사를 한국어·영어·일본어로 검색하고, 근거와 함께 해석해 주는 RAG 기반 지식 서비스

- UtaTen에서 240곡(아티스트 40명 × 6곡)의 메타데이터와 가사를 수집·색인
- 질문하면 한국어 위키백과 문서를 골라 수집·색인하고, 검색된 근거만으로 질문한 언어로 답변
- 주장마다 `[근거 N]` 을 붙이고, 인용한 근거의 제목과 원문 링크 제공

| 문서 | 내용 |
|------|------|
| [`docs/SPEC.md`](docs/SPEC.md) | 요구사항 정의서 |
| [`docs/rag_pipeline.md`](docs/rag_pipeline.md) | RAG 파이프라인 설계 |
| [`docs/verification.md`](docs/verification.md) | 검증 결과 |
| [`docs/benchmark.md`](docs/benchmark.md) | 검색·답변 벤치마크 |
| [`docs/rag_comparison.md`](docs/rag_comparison.md) | RAG 사용 전후 비교 (F2015) |
| [`docs/specs/`](docs/specs) | 이슈별 상세 SPEC |
| [`AGENTS.md`](AGENTS.md) | 개발 흐름 |

## 실행 방법

Python 3.10 이상 (CI는 3.12).

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env               # GMS_KEY, GMS_BASE_URL, WIKI_CONTACT
python scripts/crawl_songs.py      # 곡 수집 (약 15분)
python scripts/index_songs.py      # 곡 색인
python scripts/prefetch_wiki.py    # (권장) 위키 문서 미리 수집, 앱을 끈 상태에서 실행
streamlit run src/lyriclens/ui/app.py
```

임베딩 모델을 바꾸면 `data/chroma` 와 `data/cache/collected.json` 을 지우고 색인부터 다시 실행. 2026-10-21 이전 색인은 통합 곡 검색을 위해 재색인 필요

테스트:

```bash
pip install -r requirements-dev.txt
pytest -m "not live"   # 단위 테스트 (CI와 동일)
pytest -m live         # 실제 외부 호출
ruff check .
```

## 기능

| 번호 | 기능 |
|------|------|
| F2001·F2002 | 곡 메타데이터 적재·색인 |
| F2003 | 위키백과 검색어 추출 (프롬프트 1) |
| F2004 | 위키 후보 선별·수집 (프롬프트 2) |
| F2005 | 위키 문서 청킹·색인 |
| F2006 | 근거 검색·병합·중복 제거 |
| F2007 | 근거 기반 답변 (LangGraph `retrieve → generate`) |
| F2008 | 인용 근거 표시 |
| F2009 | 곡 선택·곡별 대화 기록 |
| F2010 | 가사 구절 해석, 구절로 곡 찾기 |
| F2011 | 조건 기반 곡 탐색 |
| F2012 | 진행 상태·안내 |
| F2014 | MMR 검색 (`retrieval.search_type: mmr`, 기본값 similarity) |
| F2015 | RAG 사용 전후 품질 비교 |
| 확장 | 통합 곡 검색 (제목·아티스트·별명·오탈자·가사) |

보류: F2013(HTML/JS 프론트엔드), F2016(여러 출처 결합)

## 데이터 준비와 색인

1. `config/artists.yaml` 아티스트별 UtaTen 인기곡 6곡을 파싱해 `data/songs.jsonl` 로 저장
2. `song_meta`(곡당 1청크)와 `song_lyrics`(가사 연 단위)에 upsert
3. 질문 시 위키백과 문서를 수집해 `wiki_docs` 에 색인 (같은 곡·검색어는 캐시 사용)

설정값은 모두 `config/settings.yaml` 참고

## 출처와 이용 조건

| 출처 | 용도 | 이용 조건 | 호출 간격 | 재시도 |
|------|------|-----------|-----------|--------|
| [UtaTen](https://utaten.com/) | 곡 메타데이터, 가사 | robots.txt 준수(2026-10-21), 가사는 최대 4줄 인용 + 원문 링크 | 3초 이상 | 지수 백오프 3회 |
| [한국어 위키백과](https://ko.wikipedia.org/) | 곡·아티스트·타이업 설명 | CC BY-SA 4.0, 문서 제목·원문 URL 표시, User-Agent에 연락처 포함 | 1초 이상 | 429·5xx 지수 백오프 3회 |

## 기술 스택

### 라이브러리

| 라이브러리 | 버전 |
|------------|------|
| langchain | 1.3.14 |
| langgraph | 1.2.10 |
| langchain-openai | 1.4.3 |
| langchain-chroma | 1.1.0 |
| langchain-text-splitters | 1.1.2 |
| chromadb | 1.5.9 |
| openai | 2.54.0 |
| streamlit | 1.62.0 |
| beautifulsoup4 | 4.13.4 |
| lxml | 6.0.0 |

전체 목록은 `requirements.txt` 참고

### 사용 모델 (SSAFY GMS, OpenAI 호환)

| 용도 | 모델 |
|------|------|
| 답변·구절 해석 | `gpt-6-luna` |
| 보조 작업 (검색어 추출·선별·변환) | `gpt-5.4-nano` |
| 임베딩 | `text-embedding-3-large` |
