"""설정 로더 — config/settings.yaml 과 환경변수(.env)를 읽는다. (SPEC-001)"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SETTINGS = ROOT / "config" / "settings.yaml"
REQUIRED_ENV = ("GMS_KEY", "WIKI_CONTACT")
SECTIONS = ("llm", "chunking", "retrieval", "collect", "crawl", "display", "paths")


@dataclass(frozen=True)
class Settings:
    llm: dict
    chunking: dict
    retrieval: dict
    collect: dict
    crawl: dict
    display: dict
    paths: dict
    root: Path
    gms_key: str | None = field(default=None, repr=False)
    wiki_contact: str | None = field(default=None, repr=False)

    def path(self, name: str) -> Path:
        p = Path(self.paths[name])
        return p if p.is_absolute() else self.root / p


def load_settings(path: str | Path | None = None, overrides: dict | None = None) -> Settings:
    load_dotenv(ROOT / ".env", override=False)
    path = Path(path or os.environ.get("LYRICLENS_SETTINGS") or DEFAULT_SETTINGS)
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    sections = {name: dict(data.get(name) or {}) for name in SECTIONS}
    for name, values in (overrides or {}).items():
        sections[name] = {**sections.get(name, {}), **values}
    return Settings(
        **sections,
        root=ROOT,
        gms_key=os.environ.get("GMS_KEY") or None,
        wiki_contact=os.environ.get("WIKI_CONTACT") or None,
    )


def missing_env(settings: Settings) -> list[str]:
    values = {"GMS_KEY": settings.gms_key, "WIKI_CONTACT": settings.wiki_contact}
    return [name for name in REQUIRED_ENV if not values[name]]


def load_artists(path: str | Path | None = None) -> list[dict]:
    path = Path(path) if path else load_settings().path("artists")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return list(data.get("artists") or [])
