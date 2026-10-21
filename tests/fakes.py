"""테스트 대역 모음. 외부 호출(utaten, 위키백과, LLM, 임베딩)은 여기의 가짜 객체로 바꾼다."""

from __future__ import annotations

from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures"


def fixture_text(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


class FakeResponse:
    def __init__(self, status_code: int = 200, text: str = ""):
        self.status_code = status_code
        self.text = text


class FakeSession:
    """requests.Session 대역. 준비된 응답을 차례로 돌려주고 호출을 기록한다."""

    def __init__(self, responses: list[FakeResponse] | None = None, default: str = "<html></html>"):
        self.responses = list(responses or [])
        self.default = default
        self.calls: list[dict] = []

    def get(self, url, headers=None, timeout=None, params=None):
        self.calls.append({"url": url, "headers": headers or {}, "params": params})
        if self.responses:
            resp = self.responses.pop(0)
            if isinstance(resp, Exception):
                raise resp
            return resp
        return FakeResponse(200, self.default)


class FakeClock:
    """time.monotonic / time.sleep 대역. sleep 하면 시간이 흐른다."""

    def __init__(self):
        self.now = 0.0
        self.sleeps: list[float] = []

    def monotonic(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


class FakeUtatenClient:
    """경로 → HTML 사전으로 동작하는 UtatenClient 대역."""

    def __init__(self, pages: dict[str, str]):
        self.pages = pages
        self.calls: list[str] = []

    def get(self, path: str) -> str:
        self.calls.append(path)
        from lyriclens.domain.utaten_client import FetchError

        for key, html in self.pages.items():
            if path.startswith(key):
                return html
        raise FetchError(f"404 {path}")


class FakeEmbeddings:
    """문자 bi-gram 해시 기반 결정적 임베딩. 겹치는 글자가 많을수록 가깝다."""

    dim = 64

    def _vec(self, text: str) -> list[float]:
        import hashlib
        import math

        v = [0.0] * self.dim
        grams = [text[i : i + 2] for i in range(max(len(text) - 1, 1))]
        for g in grams:
            v[int(hashlib.md5(g.encode()).hexdigest(), 16) % self.dim] += 1.0
        norm = math.sqrt(sum(x * x for x in v)) or 1.0
        return [x / norm for x in v]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._vec(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._vec(text)


def make_song(song_id="ut_aa0001", **kw):
    from lyriclens.domain.models import Song

    data = dict(
        song_id=song_id, title="星の街", title_kana="ほしのまち", artist="テスト歌手",
        artist_ko="테스트 가수", lyricist="作詞者A", composer="作曲者B", arranger=None,
        release_date="2021-04-05", tieup="TVアニメ「テスト」主題歌",
        lyrics="夜の窓に灯がともる\nねむれない僕の声\n\n星の街で待ってる\n君の名前を呼んだ",
        url=f"https://utaten.com/lyric/{song_id[3:]}/",
    )
    data.update(kw)
    return Song(**data)


class FakeMessage:
    def __init__(self, content: str):
        self.content = content


class FakeChatModel:
    """정해진 응답을 차례로 돌려주는 채팅 모델 대역. 응답이 떨어지면 마지막 응답을 반복한다."""

    def __init__(self, responses: list[str] | None = None):
        self.responses = list(responses or ["[]"])
        self.calls: list = []

    delay = 0.0

    def invoke(self, messages, **kw):
        import time

        self.calls.append(messages)
        if self.delay:
            time.sleep(self.delay)
        content = self.responses.pop(0) if len(self.responses) > 1 else self.responses[0]
        return FakeMessage(content)

    def stream(self, messages, **kw):
        text = self.invoke(messages, **kw).content
        for i in range(0, len(text), 5):
            yield FakeMessage(text[i : i + 5])


class FakeWikiClient:
    """제목 → 문서 사전으로 동작하는 위키 클라이언트 대역."""

    def __init__(self, pages: list[dict], search_map: dict[str, list[int]] | None = None):
        from lyriclens.collect.wikipedia import WikiCandidate, WikiPage

        self._cand, self._page = WikiCandidate, WikiPage
        self.pages = {p["page_id"]: p for p in pages}
        self.search_map = search_map or {}
        self.calls: list[tuple[str, object]] = []

    def search(self, query, limit):
        self.calls.append(("search", query))
        ids = self.search_map.get(query, [])[:limit]
        return [self._cand(i, self.pages[i]["title"], self.pages[i]["text"][:50]) for i in ids]

    def find_page(self, title):
        self.calls.append(("find_page", title))
        for p in self.pages.values():
            if p["title"] == title:
                return self._cand(p["page_id"], p["title"], p["text"][:50])
        return None

    def fetch(self, page_id):
        self.calls.append(("fetch", page_id))
        p = self.pages[page_id]
        return self._page(page_id, p["title"], p["url"], p["text"])

    def count(self, kind):
        return sum(1 for k, _ in self.calls if k == kind)
