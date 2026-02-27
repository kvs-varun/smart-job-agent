import json
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional


def _utc_now() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _read_json(path: str) -> List[Dict[str, Any]]:
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _write_json(path: str, data: List[Dict[str, Any]]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def track_event(db_path: str, event_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Append an analytics event to a local JSONL-like store (JSON array).

    Privacy note: keep payload minimal; avoid storing full resume/JD text.
    """

    ev = {
        "id": f"evt_{datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')}",
        "type": event_type,
        "timestamp_utc": _utc_now(),
        "payload": payload or {},
    }

    data = _read_json(db_path)
    data.append(ev)
    _write_json(db_path, data)
    return ev


def summarize_events(db_path: str) -> Dict[str, Any]:
    events = _read_json(db_path)

    counts: Dict[str, int] = {}
    for e in events:
        t = e.get("type") or "unknown"
        counts[t] = counts.get(t, 0) + 1

    generate = counts.get("generate_attempt", 0)
    downloads = counts.get("pdf_download", 0)
    outreach = counts.get("outreach_generated", 0)

    ratio = (downloads / generate) if generate else 0.0

    return {
        "total_events": len(events),
        "counts": counts,
        "generate_to_download_ratio": round(ratio, 3),
        "notes": "Local-only analytics. For public launch, add consent + retention policy.",
    }
