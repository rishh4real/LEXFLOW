"""
routes/verification.py
----------------------
Admin verification workflow for flagged cases.
- GET  /verify/flagged          → list all flagged cases for admin review
- POST /verify/{case_id}        → admin approves, rejects, or edits a case
- GET  /verify/{case_id}/detail → side-by-side AI vs student comparison for admin
"""

import json
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional

from database.db import get_connection
from auth.auth import get_current_user
from auth.roles import require_admin

router = APIRouter(prefix="/verify", tags=["Verification"])


# ── Request body ──────────────────────────────────────────────────────────────
class VerificationAction(BaseModel):
    action: str               # "approve" | "reject" | "flag"
    notes: Optional[str] = None


# ── List Flagged Cases ────────────────────────────────────────────────────────
@router.get("/flagged")
def list_flagged(current_user: dict = Depends(require_admin)):
    """
    Return all cases with status='flagged'.
    Includes the latest quiz submission scores for context.
    Admin only.
    """
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT
            c.id, c.case_number, c.pdf_path, c.status, c.created_at,
            qs.match_score, qs.submitted_at,
            u.name AS student_name, u.email AS student_email
        FROM cases c
        LEFT JOIN quiz_submissions qs ON qs.case_id = c.id
        LEFT JOIN users u ON u.id = qs.student_id
        WHERE c.status = 'flagged'
        ORDER BY c.created_at DESC
        """,
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── Side-by-side Comparison Detail ───────────────────────────────────────────
@router.get("/{case_id}/detail")
def verification_detail(case_id: int, current_user: dict = Depends(require_admin)):
    """
    Return AI extraction answers alongside student answers for comparison.
    Used in AdminPanel for side-by-side review.
    """
    conn = get_connection()

    case = conn.execute("SELECT * FROM cases WHERE id = ?", (case_id,)).fetchone()
    if not case:
        conn.close()
        raise HTTPException(status_code=404, detail="Case not found.")

    extraction = conn.execute(
        "SELECT * FROM extractions WHERE case_id = ?", (case_id,)
    ).fetchone()

    submission = conn.execute(
        """
        SELECT qs.*, u.name, u.email
        FROM quiz_submissions qs
        JOIN users u ON u.id = qs.student_id
        WHERE qs.case_id = ?
        ORDER BY qs.submitted_at DESC
        LIMIT 1
        """,
        (case_id,),
    ).fetchone()

    questions = conn.execute(
        "SELECT * FROM quiz_questions WHERE case_id = ? ORDER BY question_order",
        (case_id,),
    ).fetchall()
    conn.close()

    return {
        "case": dict(case),
        "extraction": dict(extraction) if extraction else None,
        "submission": dict(submission) if submission else None,
        "questions": [dict(q) for q in questions],
    }


# ── Admin Decision ────────────────────────────────────────────────────────────
@router.post("/{case_id}")
def verify_case(
    case_id: int,
    body: VerificationAction,
    current_user: dict = Depends(require_admin),
):
    """
    Admin approves, rejects, or re-flags a case.
    - approve → case status = 'verified' (visible to officials on dashboard)
    - reject  → case status = 'flagged' (stays in admin queue)
    - flag    → keep flagged with notes
    """
    if body.action not in ("approve", "reject", "flag"):
        raise HTTPException(status_code=400, detail="Action must be approve, reject, or flag.")

    conn = get_connection()

    case = conn.execute("SELECT id FROM cases WHERE id = ?", (case_id,)).fetchone()
    if not case:
        conn.close()
        raise HTTPException(status_code=404, detail="Case not found.")

    # Determine new case status
    new_status = {
        "approve": "verified",
        "reject": "flagged",
        "flag": "flagged",
    }[body.action]

    conn.execute(
        "UPDATE cases SET status = ? WHERE id = ?", (new_status, case_id)
    )

    conn.execute(
        """
        INSERT INTO verifications (case_id, status, reviewed_by, notes)
        VALUES (?, ?, ?, ?)
        """,
        (case_id, body.action, current_user["id"], body.notes),
    )

    conn.commit()
    conn.close()

    return {
        "message": f"Case {body.action}d successfully.",
        "case_id": case_id,
        "new_status": new_status,
    }
