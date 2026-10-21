# SPEC-017 F2014 MMR 검색 적용

- 상태: 완료
- 이슈: #34
- 구분: 확장 (심화 F2014, X-01)
- 대응 요구사항: F2014
- 관련 절: `docs/SPEC.md` §9 X-01, `docs/specs/SPEC-006-retrieve.md`, `docs/benchmark.md`

## 1. 목적
근거 검색을 유사도 순 대신 MMR(Maximal Marginal Relevance)로 할 수 있게 한다. 내용이 겹치는 청크가 근거에 몰리지 않게 하기 위해서다. 같은 질문에서 유사도와 MMR의 근거 목록이 어떻게 다른지 확인할 수 있게 한다(PRD F2014).

배경: 검증 문서 §8 한계 3에 따르면, 「밤을 달리다」 한 문서의 청크 3개가 위키 근거 5~7번을 모두 차지했다.

## 2. 설계
- 설정 `retrieval.search_type: similarity | mmr` 를 둔다. MMR일 때 쓰는 값은 다음과 같다.
  - `mmr_fetch_k`(20): 먼저 가져올 후보 수
  - `mmr_lambda`(0.5): 관련성과 다양성의 균형(1이면 유사도와 같음)
- `VectorStore.search_mmr(name, query, k, fetch_k, lambda_mult, where)`
  - 후보 `fetch_k` 개를 임베딩과 함께 가져온다.
  - 이미 고른 근거와의 최대 유사도를 빼는 방식으로 하나씩 고른다(직접 구현).
  - Chroma 의존을 줄이고, 테스트에서 결정적으로 동작하게 하려고 직접 구현한다.
- `retrieve()` 는 `search_type` 이 mmr이면 `wiki_docs`·`song_lyrics` 검색에 MMR을 쓴다. 곡 정보를 1번에 고정하는 규칙은 그대로다.
- 비교 도구 `scripts/compare_retrieval.py`: QA 벤치마크의 질문을 대상으로, 같은 질문을 similarity·mmr로 검색해 근거 목록을 나란히 출력한다. 다음 지표를 함께 낸다.
  - 위키 근거 중 서로 다른 문서 수
  - 근거 청크끼리의 평균 코사인 유사도(낮을수록 다양)
- 답변 품질 비교: `bench_run.py qa --modes rag rag_mmr` 로 정답률·근거 제시율 차이를 잰다.

## 3. 수용 기준 (AC)
| 테스트 ID | 조건 | 기대 결과 |
|-----------|------|-----------|
| T-F2014-1 | 거의 같은 청크 3개 + 다른 청크 2개, k=3 | 유사도 검색은 같은 청크를 몰아 고르고, MMR은 다른 청크를 포함 |
| T-F2014-2 | `mmr_lambda=1.0` | 유사도 검색과 같은 순서 |
| T-F2014-3 | `search_type: mmr` 로 retrieve | 곡 정보 1번 고정·곡 범위 필터 유지, 위키 근거 수 = wiki_top_k |
| T-F2014-4 | 비교 도구 요약 함수 | 서로 다른 문서 수·평균 유사도를 계산 |
| 측정 | QA 벤치마크 90문항 | similarity vs mmr: 근거 다양성·정답률·근거 제시율을 `docs/benchmark.md` 에 기록 |

## 4. 결과와 결정 (2026-10-21)
- 근거 다양성은 높아졌다. 서로 다른 문서 수는 1.59 → 1.76, 근거끼리 평균 유사도는 0.512 → 0.435다.
- 답변 품질은 조금 낮아졌다. LLM 판정 정답률이 0.962 → 0.897이다. 실제 원인은 정답 청크가 빠진 2건, 무관한 청크가 섞인 1건이고, 나머지는 판정 변동이다.
- 그래서 기본값은 `similarity` 를 유지하고, MMR은 설정으로 켠다. 자세한 내용은 `docs/benchmark.md` §4 에 있다.
