# SPEC-006 retrieve: 근거 검색·병합·중복 제거

- 상태: 진행 중
- 이슈: #6
- 구분: MVP
- 대응 요구사항: F2006
- 관련 절: `docs/SPEC.md` §F2006

## 1. 목적
선택한 곡의 질문에 대해 세 컬렉션에서 근거를 모아 번호가 붙은 근거 목록을 만든다. LangGraph `retrieve` 노드(SPEC-007)가 이 함수를 쓴다.

## 2. 범위
- 포함: `rag/evidence.py`(근거 형식), `rag/retrieve.py`
- 제외: 답변 생성·그래프(SPEC-007), MMR(확장 X-01)

## 3. 상세 설계
```python
@dataclass
class Evidence:
    num: int                 # 1부터
    chunk_id: str
    source_type: str         # "song_meta" | "lyrics" | "wikipedia"
    title: str               # 화면 표시용 제목
    url: str
    text: str
    metadata: dict

SOURCE_LABELS = {"song_meta": "곡 정보", "lyrics": "가사", "wikipedia": "위키백과"}

def retrieve(store, song_id: str, question: str, settings) -> list[Evidence]
```
1. `song_meta` 에서 `song_id` 를 **ID로 조회**(검색 아님) → 있으면 항상 1번
2. `song_lyrics` 를 `where={"song_id": song_id}` 로 `retrieval.lyrics_top_k` 개 검색
3. `wiki_docs` 를 `where={"song_id": song_id}` 로 `retrieval.wiki_top_k` 개 검색
4. 순서 메타 → 가사 → 위키로 합치고, 같은 `chunk_id` 와 같은 `(source_type, 문서 ID, 본문)` 은 처음 것만 남긴다
5. 번호를 1부터 다시 매긴다
- 제목 규칙: 곡 정보 `"{title} — {artist}"`, 가사 `"{title} 가사 ({stanza_seq+1}연)"`, 위키 `doc_title`
- 곡 메타가 없으면(색인 안 됨) 가사·위키 근거만 돌려준다.

## 4. 수용 기준 (AC)
| 테스트 ID | 조건 | 기대 결과 |
|-----------|------|-----------|
| T-F2006-1 | 아무 질문 | 1번 근거가 선택 곡의 `song_meta` |
| T-F2006-2 | 다른 곡의 위키·가사 청크가 더 비슷함 | 근거에 들어가지 않음 |
| T-F2006-3 | 같은 본문의 청크가 중복 | 하나만 남음 |
| T-F2006-4 | `wiki_top_k` 3 → 6 (문서 충분) | 위키 근거 수 3 → 6 |
| T-F2006-5 | 근거 번호·출처 유형 | 1..N 연속, source_type·제목·URL 채워짐 |

## 5. 테스트 계획
- `tests/test_retrieve.py` — `FakeEmbeddings` + 실제 Chroma(`tmp_path`)

## 6. 결정 필요 사항
- 없음
