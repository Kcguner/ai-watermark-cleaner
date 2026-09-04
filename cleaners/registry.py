import json
import os
import sys
from functools import lru_cache
from pathlib import Path


def _resolve_registry_path() -> Path:
    """Resolve the watermarks.json location.

    Tries (in order):
    (c) env AWC_CONFIG override, if set;
    (a) frozen bundle path Path(sys._MEIPASS)/config/watermarks.json;
    (b) source tree path Path(__file__).parent.parent/config/watermarks.json.
    """
    override = os.environ.get("AWC_CONFIG")
    if override:
        return Path(override)
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / "config" / "watermarks.json"  # type: ignore[attr-defined]
    return Path(__file__).resolve().parent.parent / "config" / "watermarks.json"


REGISTRY_PATH = _resolve_registry_path()

@lru_cache(maxsize=1)
def _load():
    with open(REGISTRY_PATH, encoding="utf-8") as f:
        data = json.load(f)
    return {s["source"]: s for s in data["signatures"]}

def get_signature(source: str) -> dict:
    sigs = _load()
    key = source.strip().lower()
    if key not in sigs:
        raise KeyError(f"unknown source: {source!r}, known: {sorted(sigs)}")
    return sigs[key]

def list_sources() -> list[str]:
    return sorted(_load().keys())
