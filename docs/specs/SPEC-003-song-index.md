# SPEC-003 항목 텍스트·song_meta/song_lyrics 색인

- 상태: 완료
- 이슈: #3
- 구분: MVP
- 대응 요구사항: F2001, F2002
- 관련 절: `docs/SPEC.md` §3.2, §3.3, §F2001, §F2002

## 1. 목적
수집한 곡을 검색할 수 있도록 곡당 1청크(`song_meta`)와 가사 연 청크(`song_lyrics`)로 Chroma에 색인한다.

## 2. 범위
- 포함: `domain/item_text.py`, `domain/lyrics.py`, `domain/documents.py`(곡 → 색인 문서 변환), `index/store.py`(Chroma 래퍼), `llm.py`(임베딩·채팅 모델 생성), `scripts/index_songs.py`
- 제외: 위키 문서 색인(SPEC-005)

## 3. 상세 설계

### 3.1 색인 문서 형식 (도메인 독립)
```python
@dataclass
class IndexDoc:
    id: str
    text: str
    metadata: dict   # None 값은 넣지 않는다 (Chroma 제약)
```

### 3.2 도메인 변환 (`domain/`)
- `build_item_text(song, max_chars) -> str`: §3.3 형식. 값 없는 줄 생략. `max_chars` 초과 시 가사 끝을 잘라 맞춘다.
- `split_stanzas(lyrics, max_lines) -> list[str]`: 빈 줄 기준으로 연을 나누고, `max_lines` 를 넘는 연은 `max_lines` 줄씩 다시 나눈다. 빈 연은 버린다.
- `quote_lines(text, max_lines) -> str`: 앞에서 `max_lines` 줄만 남기고 잘렸으면 `…` 줄을 붙인다. (화면 인용 제한 D-02, 이후 이슈에서 재사용)
- `song_meta_doc(song, max_chars) -> IndexDoc`: id=`song_id`, 메타데이터는 §3.2 `song_meta` 필드 (`release_year` int 포함, `source_type="song_meta"`)
- `song_lyric_docs(song, max_lines) -> list[IndexDoc]`: id=`{song_id}:L{seq}` (seq 0부터), `source_type="lyrics"`

### 3.3 Vector Store (`index/store.py`)
```python
class VectorStore:
    def __init__(self, persist_dir, embeddings): ...
    def collection(self, name) -> langchain_chroma.Chroma
    def upsert(self, name, docs: list[IndexDoc], batch_size=64) -> int   # 같은 id는 덮어씀
    def count(self, name) -> int                                          # 컬렉션 없으면 0
    def get(self, name, ids: list[str]) -> list[IndexDoc]
    def search(self, name, query, k, where=None) -> list[tuple[IndexDoc, float]]
```
- 컬렉션 거리 함수는 cosine (`collection_metadata={"hnsw:space": "cosine"}`), `search` 점수는 `1 - distance`.

### 3.4 모델 생성 (`llm.py`)
- `make_embeddings(settings)`, `make_chat(settings)`: 모델명은 설정에서, 키와 API 주소는 환경변수(`GMS_KEY`, `GMS_BASE_URL`)에서 읽는다. 키가 없으면 `MissingKeyError`.

### 3.5 스크립트
`python scripts/index_songs.py` → `songs.jsonl` 을 읽어 두 컬렉션에 upsert, `song_meta N건 / song_lyrics M건` 출력. 곡이 0건이면 수집 스크립트 실행 안내 후 종료 코드 1.

## 4. 수용 기준 (AC)
| 테스트 ID | 조건 | 기대 결과 |
|-----------|------|-----------|
| T-F2001-3 | 항목 텍스트 생성 | 제목·읽기·아티스트(일/한)·크레딧·발매일·가사 포함, 빈 값 줄 없음, max_chars 이하 |
| T-F2002-1 | N곡 색인 | `song_meta` count = N |
| T-F2002-2 | 같은 곡 두 번 색인 | count 변화 없음 |
| T-F2002-3 | 스크립트 실행 함수 | 색인 건수 출력 |
| T-F2002-4 | 저장 메타데이터 | 필수 필드 존재, None 값 없음, release_year는 int |
| T-LYR-1 | 연 분할 | 빈 줄 기준, max_lines 초과 연은 다시 분할 |
| T-LYR-2 | 인용 제한 | max_lines 줄 + `…` |
| T-LLM-1 | 키 없음 | `make_embeddings` 가 MissingKeyError |

## 5. 테스트 계획
- `tests/test_item_text.py`, `tests/test_lyrics.py`, `tests/test_store.py`, `tests/test_index_songs.py`, `tests/test_llm.py`
- 대역: `FakeEmbeddings`(문자 n-gram 해시 기반 결정적 벡터), 실제 Chroma(`tmp_path`)

## 6. 결정 필요 사항
- 없음
