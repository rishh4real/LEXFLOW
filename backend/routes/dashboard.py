"""
routes/dashboard.py
-------------------
Government official dashboard routes.
- GET /dashboard/cases           → verified cases with urgency metadata
- GET /dashboard/cases/{id}      → full case detail with action plan
- GET /dashboard/departments     → list of unique responsible departments
"""

import json
from datetime import datetime, date
from fastapi import APIRouter, Depends, HTTPException
from typing import Optional

from database.db import get_connection
from auth.auth import get_current_user
from auth.roles import require_admin_or_official

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


def compute_urgency(deadline_str: Optional[str]) -> str:
    """
    Compute urgency from compliance_deadline.
    Red   → deadline within 7 days
    Amber → deadline within 30 days
    Green → more than 30 days away or no deadline
    """
    if not deadline_str:
        return "green"
    try:
        deadline = datetime.strptime(deadline_str, "%Y-%m-%d").date()
        days_left = (deadline - date.today()).days
        if days_left <= 7:
            return "red"
        elif days_left <= 30:
            return "amber"
        else:
            return "green"
    except (ValueError, TypeError):
        return "green"


# ── Verified Cases List ───────────────────────────────────────────────────────
@router.get("/cases")
def get_dashboard_cases(
    department: Optional[str] = None,
    search: Optional[str] = None,
    current_user: dict = Depends(require_admin_or_official),
):
    """
    Return all verified cases for the government dashboard.
    Supports filtering by department and keyword search.
    Includes urgency badge computed from compliance_deadline.
    """
    conn = get_connection()

    query = """
        SELECT
            c.id, c.case_number, c.status, c.created_at,
            e.parties, e.date_of_order, e.compliance_deadline,
            e.responsible_dept, e.action_plan, e.appeal_window
        FROM cases c
        LEFT JOIN extractions e ON e.case_id = c.id
        WHERE c.status = 'verified'
    """
    params = []

    if department:
        query += " AND e.responsible_dept LIKE ?"
        params.append(f"%{department}%")

    if search:
        query += " AND (c.case_number LIKE ? OR e.parties LIKE ? OR e.key_directions LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%", f"%{search}%"])

    query += " ORDER BY c.created_at DESC"
    rows = conn.execute(query, params).fetchall()
    conn.close()

    results = []
    for r in rows:
        item = dict(r)
        item["urgency"] = compute_urgency(item.get("compliance_deadline"))
        if item.get("action_plan"):
            try:
                item["action_plan"] = json.loads(item["action_plan"])
            except Exception:
                pass
        results.append(item)

    return results


# ── Unique Departments ────────────────────────────────────────────────────────
@router.get("/departments")
def get_departments(current_user: dict = Depends(require_admin_or_official)):
    """Return list of unique responsible departments from verified cases."""
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT DISTINCT e.responsible_dept
        FROM extractions e
        JOIN cases c ON c.id = e.case_id
        WHERE c.status = 'verified' AND e.responsible_dept IS NOT NULL
        ORDER BY e.responsible_dept
        """
    ).fetchall()
    conn.close()
    return [r["responsible_dept"] for r in rows]


# ── Single Case Detail ────────────────────────────────────────────────────────
@router.get("/cases/{case_id}")
def get_dashboard_case(
    case_id: int,
    current_user: dict = Depends(require_admin_or_official),
):
    """Full case detail including action plan and source references."""
    conn = get_connection()
    case = conn.execute("SELECT * FROM cases WHERE id = ? AND status = 'verified'", (case_id,)).fetchone()
    if not case:
        conn.close()
        raise HTTPException(status_code=404, detail="Verified case not found.")

    extraction = conn.execute(
        "SELECT * FROM extractions WHERE case_id = ?", (case_id,)
    ).fetchone()
    conn.close()

    result = {"case": dict(case)}
    if extraction:
        ext = dict(extraction)
        for field in ("action_plan", "source_references"):
            if ext.get(field):
                try:
                    ext[field] = json.loads(ext[field])
                except Exception:
                    pass
        result["extraction"] = ext
        result["urgency"] = compute_urgency(ext.get("compliance_deadline"))

    return result
