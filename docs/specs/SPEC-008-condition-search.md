# SPEC-008 조건 기반 곡 탐색

- 상태: 완료
- 이슈: #8
- 구분: MVP
- 대응 요구사항: F2011
- 관련 절: `docs/SPEC.md` §F2011

## 1. 목적
"비 오는 날 듣기 좋은 이별 노래", "2020년 이후 애니 주제가" 같은 자연어 조건(ko/en/ja)으로 조건에 맞는 곡만 골라 보여준다. 고른 곡을 누르면 그 곡의 대화로 이어진다(화면 연결은 SPEC-010).

## 2. 범위
- 포함: `services/condition_search.py`, `rag/prompts.py`(조건 해석·선별 프롬프트)
- 제외: 카드 UI(SPEC-010)

## 3. 상세 설계
```python
@dataclass
class SongMatch:
    song_id: str; title: str; artist: str; year: int | None; url: str; reason: str

@dataclass
class ConditionResult:
    matches: list[SongMatch]
    status: str            # "ok" | "empty"
    year_filter: dict | None

def search_by_condition(condition: str, store, chat, settings) -> ConditionResult
```
1. **조건 해석**(`CONDITION_PARSE` 프롬프트): `{"query": 검색 문장, "year_from": int|null, "year_to": int|null}` JSON. 파싱 실패 시 `query=condition`, 연도 필터 없음
2. **후보 검색**: `song_meta` 에서 `query` 로 `retrieval.condition_candidates` 곡. 연도가 있으면 `where` 에 `release_year` `$gte`/`$lte` (둘 다면 `$and`)
3. **선별**(`CONDITION_SELECT` 프롬프트): 후보마다 `song_id | 제목 | 아티스트 | 연도 | 타이업 | 가사 앞 3줄` 을 주고 조건에 맞는 곡만 `[{"song_id": ..., "reason": 조건 언어로 한 줄}]` JSON으로 받음. 근거로 판단할 수 없으면 고르지 않게 한다
4. 후보에 없는 `song_id` 는 버리고, LLM이 준 순서를 유지. 결과가 없으면 `status="empty"`
- 후보 검색 결과가 0곡이면 선별 LLM을 부르지 않는다.

## 4. 수용 기준 (AC)
| 테스트 ID | 조건 | 기대 결과 |
|-----------|------|-----------|
| T-F2011-1 | 선별이 후보에 없는 ID 반환 | 결과에서 빠짐 |
| T-F2011-2 | 선별이 `[]` | `status="empty"` |
| T-F2011-3 | 해석 결과 `year_from=2020` | 조회 `where` 에 `release_year >= 2020`, 2019년 곡은 후보에 없음 |
| T-F2011-4 | 해석 응답 파싱 실패 | 원문 조건으로 검색, 연도 필터 없음 |
| T-F2011-5 | 선별 프롬프트 | 후보의 제목·아티스트·연도·타이업 포함, 결과에 이유 포함 |

## 5. 테스트 계획
- `tests/test_condition_search.py` — `FakeChatModel`, `FakeEmbeddings`, 실제 Chroma(`tmp_path`)

## 6. 결정 필요 사항
- 없음
