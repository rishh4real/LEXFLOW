"""
database/local_store.py
-----------------------
In-memory fallback for local development when MongoDB is unavailable.
"""

from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4

UPLOAD_DIR = Path(__file__).resolve().parents[1] / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

cases: dict[str, dict] = {}
extractions: dict[str, dict] = {}


def serialize_case(case: dict) -> dict:
    data = dict(case)
    created_at = data.get("created_at")
    if created_at and hasattr(created_at, "isoformat"):
        data["created_at"] = created_at.isoformat()
    return data


def create_case(filename: str, content: bytes, uploaded_by: str) -> dict:
    case_id = uuid4().hex
    safe_name = f"{case_id}_{Path(filename).name}"
    path = UPLOAD_DIR / safe_name
    path.write_bytes(content)

    case = {
        "id": case_id,
        "pdf_path": str(path),
        "pdf_url": f"/files/local-{safe_name}",
        "status": "pending",
        "uploaded_by": uploaded_by,
        "created_at": datetime.utcnow(),
        "case_number": f"LOCAL-{case_id[:8].upper()}",
    }
    cases[case_id] = case
    return serialize_case(case)


def build_fallback_extraction(case_id: str, raw_text: str = "") -> dict:
    case = cases.get(case_id, {})
    today = datetime.utcnow().date()
    deadline = today + timedelta(days=30)
    parties = "Parties pending extraction"
    if raw_text:
        first_line = next((line.strip() for line in raw_text.splitlines() if line.strip()), "")
        if first_line:
            parties = first_line[:140]

    extraction = {
        "case_id": case_id,
        "case_number": case.get("case_number", f"LOCAL-{case_id[:8].upper()}"),
        "parties": parties,
        "date_of_order": today.isoformat(),
        "key_directions": "Uploaded locally. Full AI extraction is pending until the external AI and database services are available.",
        "compliance_deadline": deadline.isoformat(),
        "appeal_window": "Not extracted",
        "responsible_dept": "Pending review",
        "action_plan": {
            "recommendation": "review",
            "urgency": "medium",
            "required_action": "Review the uploaded judgment and complete verification.",
        },
        "source_references": {
            "compliance_deadline": "Local fallback extraction.",
            "responsible_department": "Local fallback extraction.",
        },
        "confidence_score": 0.0,
        "created_at": datetime.utcnow(),
    }
    extractions[case_id] = extraction
    if case_id in cases:
        cases[case_id].update({
            "case_number": extraction["case_number"],
            "status": "flagged",
        })
    return extraction


def serialize_extraction(extraction: dict) -> dict:
    data = dict(extraction)
    created_at = data.get("created_at")
    if created_at and hasattr(created_at, "isoformat"):
        data["created_at"] = created_at.isoformat()
    return data
