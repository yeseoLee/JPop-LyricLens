"""한국어 위키백과 클라이언트와 오프라인 묶음 클라이언트 (SPEC-004 §3.2)."""

from __future__ import annotations

import json
import re
import time
from pathlib import Path

from lyriclens.collect.models import WikiCandidate, WikiPage
from lyriclens.http import PoliteSession

API_URL = "https://ko.wikipedia.org/w/api.php"
TAG = re.compile(r"<[^>]+>")

__all__ = ["WikiClient", "BundleWikiClient", "WikiCandidate", "WikiPage"]


class WikiClient:
    def __init__(self, contact=None, interval_sec=1.0, max_retries=3, session=None,
                 sleep=time.sleep, clock=time.monotonic):
        self.http = PoliteSession(contact, interval_sec, max_retries, session, sleep, clock)

    def _query(self, **params) -> dict:
        params = {"action": "query", "format": "json", "formatversion": 2, **params}
        return json.loads(self.http.get(API_URL, params=params).text).get("query", {})

    def search(self, query: str, limit: int) -> list[WikiCandidate]:
        rows = self._query(list="search", srsearch=query, srlimit=limit).get("search", [])
        return [WikiCandidate(r["pageid"], r["title"], TAG.sub("", r.get("snippet", "")))
                for r in rows]

    def find_page(self, title: str) -> WikiCandidate | None:
        pages = self._query(titles=title, redirects=1).get("pages", [])
        page = pages[0] if pages else None
        if not page or page.get("missing") or "pageid" not in page:
            return None
        return WikiCandidate(page["pageid"], page["title"], "")

    def fetch(self, page_id: int) -> WikiPage:
        page = self._query(prop="extracts|info", explaintext=1, inprop="url",
                           pageids=page_id)["pages"][0]
        return WikiPage(page["pageid"], page["title"], page.get("fullurl", ""),
                        page.get("extract", ""))


class BundleWikiClient:
    """data/docs_bundle/*.json 으로 위키 클라이언트를 대신한다 (외부 호출 제한 환경)."""

    def __init__(self, bundle_dir: str | Path):
        self.pages: dict[int, WikiPage] = {}
        for path in sorted(Path(bundle_dir).glob("*.json")):
            d = json.loads(path.read_text(encoding="utf-8"))
            self.pages[int(d["page_id"])] = WikiPage(int(d["page_id"]), d["title"], d["url"],
                                                     d["text"])

    def search(self, query: str, limit: int) -> list[WikiCandidate]:
        hits = [p for p in self.pages.values() if query in p.title or query in p.text]
        return [WikiCandidate(p.page_id, p.title, p.text[:200]) for p in hits[:limit]]

    def find_page(self, title: str) -> WikiCandidate | None:
        for p in self.pages.values():
            if p.title == title:
                return WikiCandidate(p.page_id, p.title, p.text[:200])
        return None

    def fetch(self, page_id: int) -> WikiPage:
        return self.pages[page_id]
