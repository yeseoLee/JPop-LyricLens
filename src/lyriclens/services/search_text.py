"""검색어 정규화·로마자 변환·유사도 (SPEC-016 §2.1)."""

from __future__ import annotations

import unicodedata
from difflib import SequenceMatcher

_BASE = dict(zip(
    "あいうえおかきくけこさしすせそたちつてとなにぬねのはひふへほまみむめもやゆよらりるれろわをん"
    "がぎぐげござじずぜぞだぢづでどばびぶべぼぱぴぷぺぽぁぃぅぇぉゃゅょゎゔ",
    "a i u e o ka ki ku ke ko sa shi su se so ta chi tsu te to na ni nu ne no ha hi fu he ho "
    "ma mi mu me mo ya yu yo ra ri ru re ro wa o n ga gi gu ge go za ji zu ze zo da ji zu de do "
    "ba bi bu be bo pa pi pu pe po a i u e o ya yu yo wa vu".split(), strict=True,
))
_YOON = {"ゃ": "a", "ゅ": "u", "ょ": "o"}


def _to_hiragana(text: str) -> str:
    return "".join(chr(ord(c) - 0x60) if "ァ" <= c <= "ヶ" else c for c in text)


def normalize_query(text: str) -> str:
    """NFKC → 소문자 → 가타카나를 히라가나로 → 장음·공백·문장부호·기호 제거."""
    text = _to_hiragana(unicodedata.normalize("NFKC", text).casefold())
    return "".join(c for c in text if c != "ー" and unicodedata.category(c)[0] not in "PZS")


def kana_to_romaji(kana: str) -> str:
    """히라가나 → 헵번식 로마자 (요음·촉음 처리, 히라가나가 아닌 글자는 그대로)."""
    out: list[str] = []
    double = False
    for c in _to_hiragana(kana):
        if c == "っ":
            double = True
            continue
        if c in _YOON and out and len(out[-1]) >= 2 and out[-1].endswith("i"):
            prev = out.pop()
            out.append((prev[:-1] if prev[:-1] in ("sh", "ch", "j") else prev[:-1] + "y")
                       + _YOON[c])
            continue
        roma = _BASE.get(c, c)
        if double and roma and roma[0].isalpha():
            roma = ("t" if roma.startswith("ch") else roma[0]) + roma
        double = False
        out.append(roma)
    return "".join(out)


def _bigrams(text: str) -> set[str]:
    return {text[i:i + 2] for i in range(len(text) - 1)} or {text}


def edit_distance(a: str, b: str, limit: int = 3) -> int:
    """레벤슈타인 거리 (limit 를 넘으면 limit+1 로 끊는다)."""
    if abs(len(a) - len(b)) > limit:
        return limit + 1
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        cur = [i]
        for j, cb in enumerate(b, start=1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return min(prev[-1], limit + 1)


def _typo_score(query: str, name: str) -> float:
    """흔한 오탈자: 3자 이상에서 1글자, 6자 이상에서 2글자 차이."""
    shorter = min(len(query), len(name))
    dist = edit_distance(query, name)
    if dist == 1 and shorter >= 3:
        return 0.85
    if dist == 2 and shorter >= 6:
        return 0.8
    return 0.0


def similarity(query: str, name: str) -> float:
    """정규화된 두 문자열의 유사도: 완전 일치 1.0, 포함 0.9, 그 밖에는 문자 유사도."""
    if not query or not name:
        return 0.0
    if query == name:
        return 1.0
    if len(name) >= 3 and name in query or len(query) >= 3 and query in name:
        return 0.9
    a, b = _bigrams(query), _bigrams(name)
    dice = 2 * len(a & b) / (len(a) + len(b))
    return max(dice * 0.95, SequenceMatcher(None, query, name).ratio() * 0.95,
               _typo_score(query, name))
