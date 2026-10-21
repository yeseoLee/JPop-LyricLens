"""실행 환경 점검 — 키·색인·연락처 (SPEC-010 §3.3, F2012)."""

from __future__ import annotations

from dataclasses import dataclass, field

from lyriclens.config import Settings, missing_env


@dataclass
class EnvStatus:
    status: str                       # "missing_key" | "no_index" | "ok"
    warnings: list[str] = field(default_factory=list)


def check_environment(settings: Settings, meta_count: int) -> EnvStatus:
    missing = missing_env(settings)
    warnings = ["missing_contact"] if "WIKI_CONTACT" in missing else []
    if "GMS_KEY" in missing or "GMS_BASE_URL" in missing:
        return EnvStatus("missing_key", warnings)
    if meta_count == 0:
        return EnvStatus("no_index", warnings)
    return EnvStatus("ok", warnings)
