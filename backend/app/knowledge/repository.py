import json
from pathlib import Path


_KNOWLEDGE_FILE = Path(__file__).with_name("cotton_nalgonda.json")


def get_verified_guidance(query: str) -> dict | None:
    """Return a clearly-labelled demonstration record; never assert a diagnosis."""
    records = json.loads(_KNOWLEDGE_FILE.read_text(encoding="utf-8"))
    lowered = query.lower()
    if any(term in lowered for term in ("పసుప", "yellow", "ఆకులు")):
        return records[0]
    if any(term in lowered for term in ("పురుగు", "ముడత", "pest")):
        return records[1]
    return None


def list_guidance() -> list[dict]:
    return json.loads(_KNOWLEDGE_FILE.read_text(encoding="utf-8"))
