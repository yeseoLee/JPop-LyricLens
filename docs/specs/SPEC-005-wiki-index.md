# SPEC-005 위키 문서 청킹·색인

- 상태: 완료
- 이슈: #5
- 구분: MVP
- 대응 요구사항: F2005
- 관련 절: `docs/SPEC.md` §3.2, §F2005

## 1. 목적
SPEC-004에서 수집한 위키백과 문서를 설정값대로 청킹해 `wiki_docs` 컬렉션에 색인한다.

## 2. 범위
- 포함: `index/chunking.py`(청크 분할, 청크 ID 규칙, 수집 결과 → 색인 문서), `collect/pipeline.py`(수집 + 색인을 한 번에 실행하는 함수)
- 제외: 검색(SPEC-006)

## 3. 상세 설계
```python
def split_text(text: str, chunk_size: int, chunk_overlap: int) -> list[str]
    # langchain_text_splitters.RecursiveCharacterTextSplitter
    # separators: ["\n\n", "\n", "。", ". ", " ", ""]  (한국어·일본어 문장 경계 고려)

def chunk_id(song_id: str, page_id: int, seq: int) -> str   # "{song_id}:{page_id}:{seq}"

def wiki_chunk_docs(song: SongInfo, docs: list[CollectedDoc], chunk_size, chunk_overlap,
                    collected_at: str) -> list[IndexDoc]
    # 메타데이터: song_id, song_title, doc_title, doc_id, url, query, is_primary,
    #            collected_at, source_type="wikipedia"

def collect_and_index(song, question, chat, wiki, cache, store, settings) -> CollectResult
    # collect_documents → wiki_chunk_docs → store.upsert("wiki_docs")
    # 결과에 chunk_count 를 추가해 돌려준다
```
- 청크 크기·중복 길이는 `settings.chunking` 에서만 읽는다.
- 본문이 비어 있는 문서는 청크를 만들지 않는다.

## 4. 수용 기준 (AC)
| 테스트 ID | 조건 | 기대 결과 |
|-----------|------|-----------|
| T-F2005-1 | 청크 생성 | ID가 `{song_id}:{page_id}:{seq}` |
| T-F2005-2 | 두 곡이 같은 문서를 수집해 색인 | 청크가 덮어쓰지 않고 각각 존재 |
| T-F2005-3 | `chunk_size` 1000 → 300 | 같은 문서의 청크 수 증가 |
| T-F2005-4 | 청크 메타데이터 | `doc_title, url, song_id, source_type` 등 존재 |
| T-F2005-5 | `collect_and_index` | 수집 문서가 `wiki_docs` 에 들어가고 `chunk_count` 반환 |

## 5. 테스트 계획
- `tests/test_chunking.py`, `tests/test_collect_pipeline.py`
- 대역: `FakeEmbeddings`, `FakeChatModel`, `FakeWikiClient`, 실제 Chroma(`tmp_path`)

## 6. 결정 필요 사항
- 없음
