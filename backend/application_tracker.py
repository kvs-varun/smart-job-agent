import json
import os
from datetime import datetime
from typing import Dict, List, Optional


def _read_json(path: str) -> List[Dict]:
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _write_json(path: str, data: List[Dict]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def add_application(
    db_path: str,
    company: str,
    role: str,
    job_url: str = "",
    resume_filename: str = "",
    status: str = "applied",
    notes: str = "",
) -> Dict:
    """Append a job application record to a local JSON DB."""

    record = {
        "id": f"app_{datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')}",
        "company": (company or "").strip(),
        "role": (role or "").strip(),
        "job_url": (job_url or "").strip(),
        "resume_filename": (resume_filename or "").strip(),
        "status": (status or "applied").strip(),
        "notes": (notes or "").strip(),
        "date_applied_utc": datetime.utcnow().isoformat() + "Z",
        "follow_up": "pending",
    }

    data = _read_json(db_path)
    data.append(record)
    _write_json(db_path, data)
    return record


def list_applications(db_path: str) -> List[Dict]:
    """Return all application records."""

    return _read_json(db_path)


def update_application_status(db_path: str, application_id: str, status: str, follow_up: Optional[str] = None) -> Dict:
    """Update status of an application record."""

    data = _read_json(db_path)
    for rec in data:
        if rec.get("id") == application_id:
            rec["status"] = status
            if follow_up is not None:
                rec["follow_up"] = follow_up
            _write_json(db_path, data)
            return rec

    raise KeyError("application id not found")
