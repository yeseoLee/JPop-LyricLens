"""실행 환경 점검 — 키·색인·연락처 (SPEC-010 §3.3, F2012)."""

from __future__ import annotations

from dataclasses import dataclass, field

from lyriclens.config import Settings


@dataclass
class EnvStatus:
    status: str                       # "missing_key" | "no_index" | "ok"
    warnings: list[str] = field(default_factory=list)


def check_environment(settings: Settings, meta_count: int) -> EnvStatus:
    warnings = [] if settings.wiki_contact else ["missing_contact"]
    if not settings.gms_key:
        return EnvStatus("missing_key", warnings)
    if meta_count == 0:
        return EnvStatus("no_index", warnings)
    return EnvStatus("ok", warnings)
