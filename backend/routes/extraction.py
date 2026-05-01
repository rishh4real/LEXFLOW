"""
routes/extraction.py
--------------------
Triggers AI extraction for a given case.
- POST /extract/{case_id}  → run PDF parser + Claude AI, store in extractions table
- GET  /extract/{case_id}  → return stored extraction result
Phase 1: returns mock data. Phase 4: connects real Claude API.
"""

import json
from fastapi import APIRouter, Depends, HTTPException

from database.db import get_connection
from auth.auth import get_current_user

router = APIRouter(prefix="/extract", tags=["Extraction"])


# ── Mock extraction data (Phase 1 placeholder) ────────────────────────────────
MOCK_EXTRACTION = {
    "case_number": "WP/1234/2024",
    "parties": "Ravi Kumar vs. State of Maharashtra",
    "date_of_order": "2024-11-15",
    "key_directions": "The respondent department must ensure installation of potable water supply within 90 days.",
    "compliance_deadline": "2025-02-15",
    "appeal_window": "30 days from date of order",
    "responsible_department": "Public Works Department, Maharashtra",
    "action_plan": {
        "recommendation": "comply",
        "urgency": "high",
        "required_action": "Install water supply infrastructure in village XYZ within 90 days. File compliance report with court registry.",
    },
    "source_references": {
        "compliance_deadline": "The respondent shall complete installation within a period of ninety (90) days from the date of this order.",
        "responsible_department": "The Principal Secretary, Public Works Department is directed to personally supervise the project.",
    },
    "confidence_score": 0.91,
}


# ── Trigger Extraction ────────────────────────────────────────────────────────
@router.post("/{case_id}")
def trigger_extraction(case_id: int, current_user: dict = Depends(get_current_user)):
    """
    Trigger AI extraction for a case.
    Phase 1: stores mock data in extractions table.
    Phase 4: will call llm_service.extract_case() with real PDF text.
    """
    conn = get_connection()

    # Verify case exists
    case = conn.execute("SELECT * FROM cases WHERE id = ?", (case_id,)).fetchone()
    if not case:
        conn.close()
        raise HTTPException(status_code=404, detail="Case not found.")

    # Check if already extracted
    existing = conn.execute(
        "SELECT id FROM extractions WHERE case_id = ?", (case_id,)
    ).fetchone()
    if existing:
        conn.close()
        return {"message": "Extraction already exists.", "case_id": case_id}

    # ── TODO Phase 4: replace with real LLM call ──────────────────────────────
    # from services.llm_service import extract_case
    # result = extract_case(case["raw_text"])
    result = MOCK_EXTRACTION
    # ─────────────────────────────────────────────────────────────────────────

    # Store extraction in DB
    conn.execute(
        """
        INSERT INTO extractions
          (case_id, case_number, parties, date_of_order, key_directions,
           compliance_deadline, appeal_window, responsible_dept,
           action_plan, source_references, confidence_score)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            case_id,
            result["case_number"],
            result["parties"],
            result["date_of_order"],
            result["key_directions"],
            result["compliance_deadline"],
            result["appeal_window"],
            result["responsible_department"],
            json.dumps(result["action_plan"]),
            json.dumps(result["source_references"]),
            result["confidence_score"],
        ),
    )

    # Update case status
    conn.execute(
        "UPDATE cases SET case_number = ?, status = 'pending' WHERE id = ?",
        (result["case_number"], case_id),
    )

    conn.commit()
    conn.close()

    return {"message": "Extraction complete.", "case_id": case_id, "data": result}


# ── Get Extraction ────────────────────────────────────────────────────────────
@router.get("/{case_id}")
def get_extraction(case_id: int, current_user: dict = Depends(get_current_user)):
    """Return stored extraction data for a case."""
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM extractions WHERE case_id = ?", (case_id,)
    ).fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="No extraction found for this case.")

    result = dict(row)
    # Deserialise JSON fields
    if result.get("action_plan"):
        result["action_plan"] = json.loads(result["action_plan"])
    if result.get("source_references"):
        result["source_references"] = json.loads(result["source_references"])

    return result
