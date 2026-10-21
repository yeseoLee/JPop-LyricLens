"""LLM 응답에서 JSON 꺼내기 — 코드블록·앞뒤 설명문을 허용한다."""

from __future__ import annotations

import json
import re

FENCE = re.compile(r"```(?:json)?\s*(.*?)```", re.S)


def parse_json(text: str):
    """JSON 값을 돌려주고, 찾지 못하면 ValueError."""
    text = text.strip()
    m = FENCE.search(text)
    if m:
        text = m.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    for open_ch, close_ch in (("[", "]"), ("{", "}")):
        start, end = text.find(open_ch), text.rfind(close_ch)
        if start != -1 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                continue
    raise ValueError("JSON을 찾지 못했습니다")


def invoke_json(chat, messages, expect: type, retries: int = 1):
    """expect 타입 JSON을 받을 때까지 최대 retries 번 다시 묻고, 끝내 실패하면 None."""
    for _ in range(retries + 1):
        try:
            value = parse_json(chat.invoke(messages).content)
        except ValueError:
            continue
        if isinstance(value, expect):
            return value
    return None
