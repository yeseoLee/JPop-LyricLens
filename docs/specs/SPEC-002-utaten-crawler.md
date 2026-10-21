# SPEC-002 utaten 클라이언트·파서·수집 스크립트

- 상태: 완료
- 이슈: #2
- 구분: MVP
- 대응 요구사항: F2001, NF2006, NF2007
- 관련 절: `docs/SPEC.md` §3.1, §F2001, §6

## 1. 목적
`config/artists.yaml` 의 아티스트별 인기곡을 utaten에서 수집해 `data/songs.jsonl` 로 저장한다.

## 2. 범위
- 포함: `domain/models.py`(Song), `domain/utaten_client.py`, `domain/utaten_parser.py`, `domain/crawl.py`, `scripts/crawl_songs.py`, `artists.yaml` 의 `utaten_artist_id` 채우기
- 제외: 색인(SPEC-003)

## 3. 상세 설계

### 3.1 사이트 구조 (2026-10-21 확인)
| 페이지 | URL | 추출 |
|--------|-----|------|
| 아티스트 검색 | `/search?artist_name=<이름>` | `td.searchResult__artist a[href^="/artist/"]` 의 ID와 이름 |
| 아티스트 곡 목록 | `/artist/lyric/<id>` (기본 정렬 = 人気順) | `a[href^="/lyric/"]` 의 가사 ID, 처음 나온 순서·중복 제거 |
| 가사 | `/lyric/<lyric_id>/` | 아래 3.2 |

### 3.2 가사 페이지 파싱 (`utaten_parser.parse_song(html, url) -> Song`)
- 제목: `.newLyricTitle__main` 에서 `.newLyricTitle_afterTxt`("歌詞")와 `.newLyricTitle__subTitle` 제거
- 읽기: `.newLyricTitle__kana` 에서 `よみ：` 접두어 제거
- 아티스트: `.newLyricWork__name a`
- 발매일: `.newLyricWork__date` 의 `YYYY.M.D`(월·일 0 생략 가능) → `YYYY-MM-DD`, 없으면 null
- 크레딧: `dt.newLyricWork__title` 텍스트(作詞/作曲/編曲)와 바로 다음 `dd.newLyricWork__body` 텍스트(여러 명이면 `, ` 로 연결)
- 가사: `.hiragana`. `<br>` → 줄바꿈. 원문은 `.rt` 제거, 읽기는 `.ruby` 를 `.rt` 텍스트로 바꿈. 앞뒤 공백 정리, 연속 빈 줄은 하나로.
- 로마자: `.romaji` (없으면 null)
- `song_id` = `ut_` + URL의 가사 ID
- 타이업: `.newLyricTitle__subTitle` 텍스트(예: `劇場版「チェンソーマン レゼ篇」主題歌`). 없으면 null. 세부 정보는 위키백과 수집(SPEC-004)으로 보완한다. (#14에서 수정 — 처음에는 구조화된 정보가 없다고 잘못 판단함)
- 필수 요소(제목·가사)가 없으면 `ParseError`.

### 3.3 HTTP 클라이언트 (`UtatenClient`, NF2006)
```python
UtatenClient(interval_sec=3.0, max_retries=3, user_agent=..., cache_dir=None,
             session=None, sleep=time.sleep, clock=time.monotonic)
.get(path) -> str
```
- 요청 사이 최소 `interval_sec` 간격 (`clock`/`sleep` 주입으로 테스트)
- 429·5xx·연결 오류는 `2**시도 * interval_sec` 만큼 기다렸다 최대 `max_retries` 회 재시도, 그래도 실패하면 `FetchError`. 404는 재시도하지 않음
- User-Agent: `JPopLyricLens/0.1 (+mailto:<WIKI_CONTACT>)`
- `cache_dir` 가 있으면 응답 HTML을 URL 해시 파일로 저장하고 다음 호출에서는 네트워크를 쓰지 않음 (재실행 시 사이트 부하 방지)

### 3.4 수집 (`crawl.crawl_artists(artists, client, songs_per_artist) -> CrawlResult`)
- `utaten_artist_id` 가 없으면 검색 페이지에서 이름이 정확히 일치(공백·대소문자 무시)하는 첫 결과로 정함. 못 찾으면 건너뛰고 `skipped` 에 기록
- 곡 목록을 인기순으로 훑으며 아티스트당 `songs_per_artist`곡을 채운다. 이미 수집한 곡(중복)과 실패한 곡은 개수에 넣지 않고 건너뛴다. 실패는 `errors` 에 기록
- 연락처(`WIKI_CONTACT`)가 없으면 경고 로그를 남긴다
- `artist_ko` 는 artists.yaml 값을 넣음
- `song_id` 중복은 한 번만 (F2001 T-F2001-5)
- 스크립트: `python scripts/crawl_songs.py [--limit-artists N] [--write-artist-ids]` → `songs.jsonl` 저장, 곡 수 출력, 100건 미만이면 경고. `--write-artist-ids` 는 찾은 ID를 artists.yaml 에 기록

## 4. 수용 기준 (AC)
| 테스트 ID | 조건 | 기대 결과 |
|-----------|------|-----------|
| T-F2001-1 | 합성 가사 픽스처 파싱 | 제목·읽기·아티스트·작사·작곡·편곡·발매일·가사·URL·song_id 채워짐 |
| T-F2001-2 | 루비가 있는 줄 | 원문에 rt 없음, 읽기에는 rb 대신 rt |
| T-F2001-4 | 곡 수 100 미만으로 수집 | 곡 수 출력 + 경고 |
| T-F2001-5 | 두 아티스트 목록에 같은 곡 | 한 번만 저장 |
| T-F2001-6 | 아티스트 목록 픽스처 | 순서 유지·중복 제거된 가사 ID 상위 N개 |
| T-F2001-7 | 검색 픽스처 | 이름이 일치하는 아티스트 ID 반환, 없으면 None |
| T-F2001-8 | 가사 없는 HTML | ParseError, 수집은 errors에 기록하고 계속 |
| T-F2001-9 | `2025.9.24` 날짜 | `2025-09-24` |
| T-F2001-10 | 부제목(타이업)이 있는 제목 | 제목에서 빠지고 `tieup` 에 저장 |
| T-NF2006-1 | 연속 요청 | 두 요청 간격 ≥ interval, UA에 연락처 |
| T-NF2006-2 | 429 후 200 | 재시도해 성공, 404는 즉시 실패 |
| T-NF2006-3 | cache_dir 지정 후 같은 URL 2회 | 네트워크 호출 1회 |

## 5. 테스트 계획
- `tests/test_utaten_parser.py`, `tests/test_utaten_client.py`, `tests/test_crawl.py`
- 픽스처: `tests/fixtures/utaten_*.html` (합성 HTML, 직접 지은 가사)
- live: `tests/test_utaten_live.py` (실제 1곡 파싱, `@pytest.mark.live`)

## 6. 결정 필요 사항
- 없음
