"""화면에 보이는 문구 모음 (F2012, NF2004). 키·트레이스백·프롬프트 전문은 넣지 않는다."""

APP_TITLE = "JPop LyricLens"
APP_CAPTION = "일본어 가사를 한국어·English·日本語로 검색하고, 근거와 함께 해석합니다."

MISSING_KEY = """GMS_KEY 또는 GMS_BASE_URL 이 설정되지 않았습니다.
프로젝트 폴더의 .env 파일에 GMS_KEY=발급받은_키 와 GMS_BASE_URL=API_주소 를 넣고
앱을 다시 실행하세요."""
NO_INDEX = """곡 색인이 비어 있습니다. 아래 명령을 차례로 실행하세요.
python scripts/crawl_songs.py
python scripts/index_songs.py"""
MISSING_CONTACT = (
    "WIKI_CONTACT(연락처 이메일)가 없어 위키백과 호출 예절을 지킬 수 없습니다. "
    ".env 에 설정하세요."
)
GENERIC_ERROR = "처리 중 문제가 발생했습니다. 잠시 후 다시 시도해 주세요."

COPYRIGHT_NOTICE = (
    "가사 저작권은 각 권리자에게 있습니다. 가사 전문은 원문 사이트(UtaTen)에서 확인하세요."
)
TRANSLATION_NOTICE = "번역과 해석은 참고용이며, 근거 문서로 확인된 내용만 담습니다."

SIDEBAR_SELECT = "곡 선택"
SIDEBAR_PLACEHOLDER = "곡 제목이나 아티스트를 입력하세요"
INDEX_COUNT = "곡 색인: {count}곡"
ORIGINAL_LINK = "UtaTen 원문"

TAB_CHAT = "💬 질문하기"
TAB_CONDITION = "🔎 조건으로 찾기"
TAB_INTERPRET = "📖 구절 해석"
TAB_PHRASE = "🎵 구절로 곡 찾기"

SELECT_SONG_FIRST = "왼쪽에서 곡을 먼저 선택하세요."
CHAT_PLACEHOLDER = "이 곡에 대해 물어보세요 (한국어 / English / 日本語)"

STEP_RUNNING = "문서를 찾고 답변을 만드는 중…"
STEP_QUERIES = "검색어 추출: {detail}"
STEP_COLLECT = "문서 수집: {detail}"
STEP_COLLECT_CACHED = "이미 수집한 검색어 {count}개는 다시 수집하지 않았습니다."
STEP_COLLECT_FAILED = "외부 문서를 가져오지 못해 이미 색인된 근거로 답합니다."
STEP_INDEX = "색인: 새 문서 청크 {count}개"
STEP_ANSWER = "답변 생성 중"
STEP_DONE = "완료"
NO_WIKI_DOCS = "외부 문서를 찾지 못해 곡 정보와 가사만으로 답합니다."

EVIDENCE_HEADER = "답변에 사용한 근거 {count}건"
NO_CITATION = "답변에 인용된 근거가 없습니다. 내용을 그대로 믿기 전에 원문을 확인하세요."

CONDITION_INPUT = "어떤 곡을 찾나요? 예: 비 오는 날 듣기 좋은 이별 노래, 2020년 이후 애니 주제가"
CONDITION_EMPTY = "조건에 맞는 곡을 찾지 못했습니다. 조건을 바꿔 보세요."
OPEN_CHAT = "이 곡으로 대화하기"
SWITCHED = "'{title}'을(를) 선택했습니다. 질문하기 탭에서 이어서 물어보세요."

INTERPRET_PICK = "연 선택 (첫 줄만 표시)"
INTERPRET_INPUT = "또는 해석할 구절을 붙여 넣으세요"
INTERPRET_LANG = "번역 언어"
INTERPRET_BUTTON = "해석하기"
INTERPRET_NOT_FOUND = "이 곡의 가사에서 찾지 못했습니다."
INTERPRET_ORIGINAL = "원문"
INTERPRET_TRANSLATION = "참고용 번역"
INTERPRET_NOTES = "표현 풀이"
INTERPRET_BACKGROUND = "곡 배경과의 연결"

PHRASE_INPUT = "기억나는 가사를 아무 언어로 입력하세요"
PHRASE_EMPTY = "일치하는 가사를 찾지 못했습니다."
SEARCH_BUTTON = "찾기"

SEARCH_LABEL = "곡 검색"
SEARCH_PLACEHOLDER = "제목·아티스트·가사·별명 무엇이든 (한/영/일)"
SEARCH_EMPTY = "검색 결과가 없습니다."
SEARCH_PICK = "이 곡 선택"
