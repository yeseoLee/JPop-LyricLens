# SPEC-001 프로젝트 골격·설정 로더·CI·보안/구조 테스트

- 상태: 완료
- 이슈: #1
- 구분: MVP
- 대응 요구사항: NF2003, NF2005, NF2007
- 관련 절: `docs/SPEC.md` §2.2, §2.3, §4, §6

## 1. 목적
이후 모든 기능 이슈가 같은 구조·설정·테스트 기반 위에서 TDD로 진행될 수 있게 한다.

## 2. 범위
- 포함: `pyproject.toml`(src 레이아웃, pytest·ruff 설정, `live` 마커), `requirements*.txt`, `config/settings.yaml`, `config/artists.yaml`, `src/lyriclens/config.py`, 하위 패키지 빈 모듈, `tests/fakes.py` 기본 대역, 보안·구조 테스트
- 제외: 기능 구현 (이슈 2 이후)

## 3. 상세 설계

### 3.1 설정 로더 `lyriclens.config`
```python
@dataclass(frozen=True)
class Settings:
    llm: dict; chunking: dict; retrieval: dict; collect: dict
    crawl: dict; display: dict; paths: dict
    gms_key: str | None          # 환경변수 GMS_KEY
    wiki_contact: str | None     # 환경변수 WIKI_CONTACT
    root: Path                   # 상대 경로 해석 기준

def load_settings(path: str | Path | None = None, overrides: dict | None = None) -> Settings
def missing_env(settings: Settings) -> list[str]   # 비어 있는 필수 환경변수 이름 목록
def load_artists(path=None) -> list[dict]          # [{name, name_ko, utaten_artist_id}]
```
- 경로 우선순위: 인자 `path` → 환경변수 `LYRICLENS_SETTINGS` → `config/settings.yaml`. 상대 경로는 프로젝트 루트 기준.
- `overrides` 에 없는 섹션 이름이 오면 `ValueError`.
- `.env` 는 `python-dotenv` 로 읽되 이미 있는 환경변수를 덮어쓰지 않는다.
- `overrides` 는 섹션 단위 얕은 병합(`{"chunking": {"chunk_size": 500}}`). 테스트·비교 실험에서 값만 바꿀 때 쓴다.
- `Settings.path(name)` 은 `paths` 값을 `root` 기준 절대 경로로 돌려준다.
- `repr(Settings)` 에 키 값이 나오지 않는다 (`gms_key` 는 `repr=False`).

### 3.2 보안·구조 검사
- `tests/test_security.py`: git이 추적하는 파일에서 `sk-[A-Za-z0-9]{20,}` 패턴과 `GMS_KEY=` 뒤에 16자 이상 영숫자 값이 오는 형태를 찾는다(빈 값·문서 예시는 허용). `git ls-files` 결과에 `.env`, `data/` 가 없어야 한다.
- `tests/test_architecture.py`: `src/lyriclens` 의 `collect, index, rag, services` 패키지 파일을 AST로 읽어 `lyriclens.domain.utaten_*` import가 없음을 확인한다.

## 4. 수용 기준 (AC)
| 테스트 ID | 조건 | 기대 결과 |
|-----------|------|-----------|
| T-CFG-1 | 기본 설정 로드 | `chunking.chunk_size == 1000`, `retrieval.wiki_top_k == 5` 등 §4 값 |
| T-CFG-2 | `overrides={"chunking":{"chunk_size":500}}` | chunk_size만 500, chunk_overlap은 200 유지 |
| T-CFG-3 | `LYRICLENS_SETTINGS` 로 다른 파일 지정 | 그 파일 값을 읽음 |
| T-NF2003-1 | GMS_KEY 비어 있음 | `missing_env()` 에 `GMS_KEY` 포함, `repr` 에 키 값 없음 |
| T-NF2003-2 | 추적 파일 스캔 | 키 패턴 0건 |
| T-NF2005-1 | 구조 검사 | 도메인 외 패키지가 utaten 모듈을 import하지 않음 |
| T-NF2007-1 | `git ls-files` | `.env`, `data/` 미포함 |
| T-CFG-4 | `load_artists()` | 40명, 각 항목에 `name`, `name_ko` |

## 5. 테스트 계획
- `tests/test_config.py`, `tests/test_security.py`, `tests/test_architecture.py`
- 대역: 없음 (`tests/fakes.py` 는 이후 이슈용 골격만)

## 6. 결정 필요 사항
- 없음
