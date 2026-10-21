# SPEC-015 검색·답변 벤치마크 데이터와 평가지표

- 상태: 진행 중
- 이슈: #32
- 구분: 확장 (F2015·F2014·통합 검색의 선행 작업)
- 대응 요구사항: 해당 없음 (F2015 비교의 기준을 만든다)
- 관련 절: `docs/SPEC.md` §9

## 1. 목적
검색과 답변 품질을 숫자로 비교할 기준을 만든다. 이후 이슈는 모두 이 벤치마크로 개선 전후를 측정한다.
- 통합 곡 검색(SPEC-016)
- MMR(SPEC-017)
- RAG 전후 비교(SPEC-018)

## 2. 범위
- 포함
  - `bench/search_cases.yaml`: 곡 찾기 케이스
  - `bench/lyric_refs.yaml`: 가사 구절 케이스의 참조
  - `bench/qa_cases.yaml`: 답변 품질 케이스
  - `src/lyriclens/bench/`: 데이터 로드, 지표, 실행기
  - `scripts/bench_build.py`: 케이스 검증과 가사 질의 생성
  - `scripts/bench_run.py`: 실행과 보고
  - `docs/benchmark.md`: 기준선 결과
- 제외: 검색 기능 개선 자체 (SPEC-016~018)

## 3. 곡 찾기 벤치마크

### 3.1 케이스 형식 (`bench/search_cases.yaml`)
```yaml
- id: S-title_ja-01
  category: title_ja          # 아래 표의 범주
  lang: ja                    # 질의 언어 ko | en | ja
  query: "夜に駆ける"
  relevant:                   # 정답 곡 (제목·아티스트로 적고 실행 때 song_id 로 바꾼다)
    - {title: "夜に駆ける", artist: "YOASOBI"}
  # 또는 relevant_artist: "YOASOBI"  → 그 아티스트의 곡 전부가 정답
  split: dev | test           # 사전·규칙을 만들 때는 dev 만 본다 (§3.4)
```

### 3.2 범주 (총 200개 안팎)
| 범주 | 내용 | 언어 | 예 | 개수 |
|------|------|------|----|------|
| `title_ja` | 원제 | ja | 夜に駆ける | 15 |
| `title_ko` | 한국어 번역·음역 제목 | ko | 밤을 달리다, 레몬, 아이돌 | 12 |
| `title_en` | 로마자·영어 번역 제목 | en | Yoru ni Kakeru, Racing into the Night | 12 |
| `artist_ja` | 아티스트 원어 | ja/en | 米津玄師, King Gnu | 10 |
| `artist_ko` | 아티스트 한국어 | ko | 요네즈 켄시, 킹누 | 10 |
| `artist_en` | 아티스트 로마자 | en | Yonezu Kenshi, Yorushika | 8 |
| `nickname` | 별명·애칭 | ko/ja/en | 요네즈, 켄시, 히게단, 미세스, 리사 | 12 |
| `abbrev` | 줄임말 | ko/ja/en | 오피히게, ヒゲダン, ずとまよ, 원오크, セカオワ | 10 |
| `typo` | 실제로 흔한 오탈자 (손으로 작성) | ko/ja/en | 夜に掛ける(변환 오류), マリーゴルド(장음 누락), 요아쏘비, Lemmon | 20 |
| `lyrics_ja` | 가사 원문 한 줄 | ja | (참조) | 20 |
| `lyrics_ko` | 가사 한 줄의 한국어 번역 | ko | (생성) | 15 |
| `lyrics_en` | 가사 한 줄의 영어 번역 | en | (생성) | 10 |
| `semantic` | 유의어·설명형 | ko/en/ja | 법의학 드라마 주제가 → Lemon, 전기톱 악마 애니 → IRIS OUT·ファイトソング | 15 |
| `tieup` | 타이업 작품명 | ko/en/ja | 주술회전 오프닝, Frieren opening | 12 |
| `mixed` | 아티스트+제목 섞기 | ko/en | 요아소비 아이돌, yonezu lemon | 10 |

### 3.3 저작권 처리
- 가사 원문은 저장소에 넣지 않는다.
- `bench/lyric_refs.yaml` 에는 `{title, artist, stanza, line}` 만 둔다. 실행 때 `data/songs.jsonl` 에서 해당 줄을 꺼내 질의로 쓴다.
- `lyrics_ko`·`lyrics_en` 질의는 `scripts/bench_build.py` 가 보조 모델로 해당 줄을 번역해 `data/bench/lyric_queries.json`(gitignore)에 한 번 만들고 고정한다. 다시 실행해도 기존 파일이 있으면 바꾸지 않는다. 생성 결과에 가나(ko·en) 또는 한글(en)이 남아 있으면 섞인 번역으로 보고 주 모델로 다시 만든다 (실제로 nano가 「꿈だったら…」처럼 섞어 냄).
- `typo` 질의는 무작위 규칙 대신 실제로 자주 나는 오류를 손으로 적는다: 일본어 IME 변환 오류(同音異字), 장음·촉음·작은 글자 누락, 한글 철자 오류, 영문 오타·누락. 원래 제목·아티스트 표기와 같으면 안 된다.

### 3.4 누수 방지
- 각 범주를 dev/test 로 반씩 나눈다.
- 이후 별명·줄임말 사전이나 규칙을 만들 때는 dev 케이스만 본다.
- 보고서에는 dev·test 를 따로 적는다.

### 3.5 지표
- 관련 곡 집합을 R, 상위 k 결과를 K 라 한다.
- **Hit@k**: K ∩ R 이 비어 있지 않으면 1 (k = 1, 5, 10)
- **Recall@k**: |K ∩ R| / min(|R|, k) — 아티스트 질의처럼 정답이 여럿일 때 의미가 있다
- **MRR@10**: 첫 정답 순위의 역수 (10위 밖이면 0)
- **nDCG@10**: 이진 관련도
- 보고 단위: 전체, 범주별, 언어별, split별. 시스템마다 질의당 평균 시간도 함께 적는다.

### 3.6 비교할 시스템 (기준선)
| 이름 | 방식 |
|------|------|
| `meta_vector` | `song_meta` 의미 유사도 검색 (항목 텍스트) |
| `lyrics_vector` | `song_lyrics` 유사도, 곡별 최고 점수 (번역 없음) |
| `phrase_search` | 구절로 곡 찾기 (F2010-b, 일본어 변환 포함) |
| `condition_search` | 조건 탐색 (F2011, LLM 선별 순서) |

통합 검색(SPEC-016)은 이 표에 `unified` 로 추가한다.

## 4. 답변 품질 벤치마크

### 4.1 케이스 형식 (`bench/qa_cases.yaml`)
```yaml
- id: Q-credit-01
  type: credit | release | tieup | background | meaning | unanswerable
  lang: ko | en | ja
  song: {title: "Lemon", artist: "米津玄師"}
  question: "이 곡의 작곡가는 누구인가요?"
  answer_keywords: [["米津玄師", "요네즈 켄시", "Kenshi Yonezu", "Yonezu Kenshi"]]   # 그룹마다 하나 이상 포함
  split: dev | test
```
- `credit`·`release`·`tieup` 의 정답은 수집 메타데이터에서 나온다.
- `background` 는 위키백과로 확인 가능한 사실이다(원작 소설 등).
- `meaning` 은 가사 구절의 뜻이다. 정답 키워드는 핵심 단어로 둔다.
- `unanswerable` 은 근거 문서로 답할 수 없는 질문이다. 정답은 "모른다고 답함"이다.
- 규모: 60개 이상 (유형별 8~12개, 언어 ko/en/ja 섞음)
- **어려운 문항(`hard: true`)**: 첫 기준선에서 유명곡 60문항은 RAG 없이도 100% 맞아(모델이 이미 앎) 정확성 비교의 변별력이 없었다. 그래서 2025~2026년 발매곡·덜 알려진 아티스트의 편곡자·정확한 발매일·타이업 문항 30개를 더한다. 정답은 수집 메타데이터에서 나온다. 보고는 `by_difficulty`(normal/hard)로 나눈다.

### 4.2 채점 (D-12: 정답 키워드 + LLM 판정 병행, 사용자 결정 2026-10-21)
- **키워드 정답**: 모든 키워드 그룹에서 하나 이상이 답변에 있다. 대소문자·전각/반각·공백은 무시한다.
- **LLM 판정**: 판정 모델(`bench.judge_model`, 기본 `gpt-6-luna`)에 질문, 참고 정답, 답변을 주고 `correct | incorrect | abstain` 을 JSON으로 받는다.
- **지표** (모드별)
  - 정답률(키워드), 정답률(LLM)
  - 두 판정의 일치율
  - 근거 제시율: 답변에 `[근거 N]` 이 있는 비율 (RAG 모드만 의미 있음)
  - 모름 인정률: `unanswerable` 에서 abstain 비율
  - 오답률: 답할 수 있는 질문에서 incorrect 비율. 지어낸 답이 여기에 잡힌다
- 모드: `rag`(현재 파이프라인, `LyricLensService.ask`), `norag`(같은 답변 모델에 근거 없이 곡 제목·아티스트와 질문만 준다. 공정한 비교를 위해 "모르면 모른다고 답하라"는 지시는 똑같이 둔다). F2015에서 비교한다.
- 설정: `bench.judge_model`(기본 `gpt-6-luna`).

## 5. 실행
```bash
python scripts/bench_build.py               # 가사 질의 생성(최초 1회), 케이스 검증
python scripts/bench_run.py search --systems meta_vector lyrics_vector phrase_search
python scripts/bench_run.py qa --modes rag norag
```
- 결과는 `data/bench/results/<시각>-<종류>.json` 에 저장한다.
- 요약 표는 표준 출력과 `docs/benchmark.md` 에 붙여 넣을 마크다운으로 낸다.

## 6. 수용 기준 (AC)
| 테스트 ID | 조건 | 기대 결과 |
|-----------|------|-----------|
| T-BENCH-1 | 지표 함수 | 손으로 계산한 예제와 Hit@k·Recall@k·MRR·nDCG 가 일치 |
| T-BENCH-2 | 케이스 파일 검증 | 모든 케이스가 스키마에 맞고 id 가 유일, 범주별 최소 개수 충족, dev/test 모두 존재 |
| T-BENCH-3 | 정답 해석 | `relevant` 의 제목·아티스트가 실제 데이터의 song_id 로 모두 풀림 (data 없으면 skip) |
| T-BENCH-4 | 가사 참조 | 참조가 존재하는 줄을 가리키고, 저장소 케이스 파일에 가사 원문이 없음 |
| T-BENCH-5 | 키워드 채점 | 대체 표기·전각/반각·대소문자 처리 |
| T-BENCH-6 | LLM 판정 파싱 | JSON 판정 파싱, 실패 시 `unknown` |
| T-BENCH-7 | 실행기 | 대역 시스템으로 돌리면 범주·언어·split별 요약이 나옴 |
| T-BENCH-9 | QA 실행기 (대역 답변·판정) | 유형별·모드별 정답률(키워드/LLM)·일치율·근거 제시율·모름 인정률·오답률 요약. 근거 없는 모드(`norag`) 프롬프트는 모르면 모른다고 답하도록 허용 |
| T-BENCH-10 | LLM 판정 프롬프트 | 질문·참고 정답·답변이 들어가고, unanswerable 은 '모른다고 답함'이 정답임을 알려 줌 |
| T-BENCH-11 | QA 요약 | `hard` 여부로 나눈 `by_difficulty` 요약이 있다 |
| T-BENCH-8 | 오탈자 케이스 | 질의가 정답 곡의 제목·아티스트 표기와 정확히 같지 않음 |

## 7. 결정 사항
- D-12 채점 방식 (위 §4.2)
- 통합 검색 기능 추가(D-13)는 SPEC-016 에서 다룬다.
