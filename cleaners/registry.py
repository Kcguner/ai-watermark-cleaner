import json
from functools import lru_cache
from pathlib import Path

REGISTRY_PATH = Path(__file__).resolve().parent.parent / "config" / "watermarks.json"

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
