"""utaten HTML 파서 (SPEC-002 §3.1, §3.2). 사이트 구조가 바뀌면 이 파일의 선택자만 고친다."""

from __future__ import annotations

import re

from bs4 import BeautifulSoup

from lyriclens.domain.models import Song

SEL_TITLE = ".newLyricTitle__main"
SEL_TITLE_SUFFIX = ".newLyricTitle_afterTxt"
SEL_SUBTITLE = ".newLyricTitle__subTitle"
SEL_KANA = ".newLyricTitle__kana"
SEL_ARTIST = ".newLyricWork__name a"
SEL_DATE = ".newLyricWork__date"
SEL_CREDIT_TITLE = "dt.newLyricWork__title"
SEL_LYRICS = ".hiragana"
SEL_ROMAJI = ".romaji"
SEL_SEARCH_ARTIST = "td.searchResult__artist a[href^='/artist/']"

CREDIT_FIELDS = {"作詞": "lyricist", "作曲": "composer", "編曲": "arranger"}
LYRIC_ID = re.compile(r"^/lyric/([a-z]{2}\d+)/$")
ARTIST_ID = re.compile(r"^/artist/(?:lyric/)?(\d+)")
BR = "\u2028"
DATE = re.compile(r"(\d{4})\.(\d{1,2})\.(\d{1,2})")


class ParseError(ValueError):
    pass


def _text(node) -> str:
    return " ".join(node.get_text(" ", strip=True).split()) if node else ""


def _lyrics_text(block, reading: bool) -> str:
    block = BeautifulSoup(str(block), "lxml")  # 원본을 바꾸지 않도록 복사본에서 작업
    for ruby in block.select(".ruby"):
        rb, rt = ruby.select_one(".rb"), ruby.select_one(".rt")
        ruby.replace_with((rt if reading else rb).get_text(strip=True) if (rb and rt) else "")
    for br in block.find_all("br"):
        br.replace_with(BR)
    # HTML 소스의 줄바꿈은 의미가 없고 <br> 만 줄 경계다
    text = re.sub(r"[ \t]*\n[ \t]*", "", block.get_text())
    return _normalize_lines(text.replace(BR, "\n"))


def _normalize_lines(text: str) -> str:
    lines = [line.strip() for line in text.split("\n")]
    out: list[str] = []
    for line in lines:
        if line or (out and out[-1]):
            out.append(line)
    while out and not out[-1]:
        out.pop()
    return "\n".join(out)


def _iso_date(match) -> str | None:
    if not match:
        return None
    year, month, day = match.groups()
    return f"{year}-{int(month):02d}-{int(day):02d}"


def parse_song(html: str, url: str) -> Song:
    soup = BeautifulSoup(html, "lxml")
    title_node = soup.select_one(SEL_TITLE)
    lyrics_node = soup.select_one(SEL_LYRICS)
    if not title_node or not lyrics_node:
        raise ParseError(f"제목 또는 가사가 없습니다: {url}")
    for suffix in title_node.select(SEL_TITLE_SUFFIX):
        suffix.decompose()
    subtitle = title_node.select_one(SEL_SUBTITLE)
    tieup = _text(subtitle) or None
    if subtitle:
        subtitle.decompose()

    match = re.search(r"/lyric/([a-z]{2}\d+)", url)
    if not match:
        raise ParseError(f"가사 ID를 찾을 수 없습니다: {url}")

    credits: dict[str, str] = {}
    for dt in soup.select(SEL_CREDIT_TITLE):
        field = CREDIT_FIELDS.get(_text(dt))
        dd = dt.find_next_sibling("dd")
        if field and dd:
            names = [_text(a) for a in dd.find_all("a")] or [_text(dd)]
            credits[field] = ", ".join(n for n in names if n) or None

    date_match = DATE.search(_text(soup.select_one(SEL_DATE)))
    romaji_node = soup.select_one(SEL_ROMAJI)
    lyrics = _lyrics_text(lyrics_node, reading=False)
    if not lyrics:
        raise ParseError(f"가사가 비어 있습니다: {url}")

    return Song(
        song_id=f"ut_{match.group(1)}",
        title=_text(title_node),
        title_kana=_text(soup.select_one(SEL_KANA)).removeprefix("よみ：").strip() or None,
        artist=_text(soup.select_one(SEL_ARTIST)),
        lyrics=lyrics,
        lyrics_kana=_lyrics_text(lyrics_node, reading=True),
        lyrics_romaji=_lyrics_text(romaji_node, reading=False) if romaji_node else None,
        release_date=_iso_date(date_match),
        tieup=tieup,
        url=url,
        **credits,
    )


def parse_artist_song_ids(html: str) -> list[str]:
    soup = BeautifulSoup(html, "lxml")
    ids: list[str] = []
    for a in soup.find_all("a", href=True):
        m = LYRIC_ID.match(a["href"])
        if m and m.group(1) not in ids:
            ids.append(m.group(1))
    return ids


def parse_search_artists(html: str) -> list[tuple[str, str]]:
    soup = BeautifulSoup(html, "lxml")
    found: list[tuple[str, str]] = []
    for a in soup.select(SEL_SEARCH_ARTIST):
        m = ARTIST_ID.match(a["href"])
        pair = (_text(a), m.group(1)) if m else None
        if pair and pair not in found:
            found.append(pair)
    return found
