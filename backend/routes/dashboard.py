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
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from typing import Optional

from database.mongo import get_db
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
async def get_dashboard_cases(
    department: Optional[str] = None,
    search: Optional[str] = None,
    current_user: dict = Depends(require_admin_or_official),
):
    """
    Return all verified cases for the government dashboard from MongoDB.
    Supports filtering by department and keyword search.
    """
    db = get_db()
    
    results = []
    async for doc in db.cases.find({"status": "verified"}).sort("created_at", -1):
        case_data = dict(doc)
        case_id = str(case_data.pop("_id"))
        case_data["id"] = case_id
        if case_data.get("uploaded_by"):
            case_data["uploaded_by"] = str(case_data["uploaded_by"])
        if case_data.get("pdf_file_id"):
            case_data["pdf_file_id"] = str(case_data["pdf_file_id"])
        
        # Fetch related extraction
        ext_data = await db.extractions.find_one({"case_id": case_id})
        if ext_data:
            ext_data = dict(ext_data)
            ext_data.pop("_id", None)
            ext_data.pop("case_id", None)
            case_data.update(ext_data)  # Flatten for easy dashboard display
        
        # Apply filters in memory
        if department and department.lower() not in (case_data.get("responsible_dept") or "").lower():
            continue
        
        if search:
            search = search.lower()
            match = (
                search in (case_data.get("case_number") or "").lower() or
                search in (case_data.get("parties") or "").lower() or
                search in (case_data.get("key_directions") or "").lower()
            )
            if not match:
                continue

        case_data["urgency"] = compute_urgency(case_data.get("compliance_deadline"))
        
        # Serialise timestamps
        if case_data.get("created_at") and hasattr(case_data["created_at"], "isoformat"):
            case_data["created_at"] = case_data["created_at"].isoformat()

        results.append(case_data)

    return results


# ── Unique Departments ────────────────────────────────────────────────────────
@router.get("/departments")
async def get_departments(current_user: dict = Depends(require_admin_or_official)):
    """Return list of unique responsible departments from verified cases in MongoDB."""
    db = get_db()
    verified_case_ids = []
    async for c in db.cases.find({"status": "verified"}, {"_id": 1}):
        verified_case_ids.append(str(c["_id"]))

    depts = set()
    async for doc in db.extractions.find({"case_id": {"$in": verified_case_ids}}):
        data = dict(doc)
        if data.get("responsible_dept"):
            depts.add(data["responsible_dept"])
            
    return sorted(list(depts))


from fastapi.responses import StreamingResponse
from fpdf import FPDF
import io

# ... existing code ...

# ── Single Case Detail ────────────────────────────────────────────────────────
@router.get("/cases/{case_id}")
async def get_dashboard_case(
    case_id: str,
    current_user: dict = Depends(require_admin_or_official),
):
    """Full case detail including action plan and source references from MongoDB."""
    db = get_db()
    try:
        case_oid = ObjectId(case_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid case id.")

    case_doc = await db.cases.find_one({"_id": case_oid})
    if not case_doc or case_doc.get("status") != "verified":
        raise HTTPException(status_code=404, detail="Verified case not found.")

    case_data = dict(case_doc)
    case_data["id"] = str(case_data.pop("_id"))
    if case_data.get("uploaded_by"):
        case_data["uploaded_by"] = str(case_data["uploaded_by"])
    if case_data.get("pdf_file_id"):
        case_data["pdf_file_id"] = str(case_data["pdf_file_id"])
    if case_data.get("created_at") and hasattr(case_data["created_at"], "isoformat"):
        case_data["created_at"] = case_data["created_at"].isoformat()

    extraction_doc = await db.extractions.find_one({"case_id": case_id})
    extraction_data = None
    if extraction_doc:
        extraction_data = dict(extraction_doc)
        extraction_data["id"] = str(extraction_data.pop("_id"))
        if extraction_data.get("created_at") and hasattr(extraction_data["created_at"], "isoformat"):
            extraction_data["created_at"] = extraction_data["created_at"].isoformat()

    result = {"case": case_data}
    if extraction_data:
        result["extraction"] = extraction_data
        result["urgency"] = compute_urgency(extraction_data.get("compliance_deadline"))

    return result


# ── Export to PDF ─────────────────────────────────────────────────────────────
@router.get("/cases/{case_id}/export")
async def export_case_pdf(
    case_id: str,
    current_user: dict = Depends(require_admin_or_official),
):
    """Generate a professional PDF summary of the court judgment and action plan."""
    case_data = await get_dashboard_case(case_id, current_user)
    extraction = case_data.get("extraction")
    
    if not extraction:
        raise HTTPException(status_code=400, detail="No extraction data available for export.")

    pdf = FPDF()
    pdf.add_page()
    
    # Header
    pdf.set_font("helvetica", "B", 16)
    pdf.cell(0, 10, "LexFlow - Court Judgment Intelligence", ln=True, align="C")
    pdf.set_font("helvetica", "B", 12)
    pdf.cell(0, 10, f"Case Number: {extraction.get('case_number', 'N/A')}", ln=True, align="C")
    pdf.ln(5)
    
    # Summary Section
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font("helvetica", "B", 11)
    pdf.cell(0, 8, " CASE SUMMARY", ln=True, fill=True)
    pdf.set_font("helvetica", "", 10)
    pdf.multi_cell(0, 6, f"Parties: {extraction.get('parties', 'N/A')}")
    pdf.cell(0, 6, f"Order Date: {extraction.get('date_of_order', 'N/A')}", ln=True)
    pdf.cell(0, 6, f"Responsible Dept: {extraction.get('responsible_dept', 'N/A')}", ln=True)
    pdf.ln(5)
    
    # Key Directions
    pdf.set_font("helvetica", "B", 11)
    pdf.cell(0, 8, " KEY JUDICIAL DIRECTIVES", ln=True, fill=True)
    pdf.set_font("helvetica", "", 10)
    pdf.multi_cell(0, 6, extraction.get("key_directions", "No directions specified."))
    pdf.ln(5)
    
    # Action Plan
    pdf.set_font("helvetica", "B", 11)
    pdf.cell(0, 8, " STRATEGIC ACTION PLAN", ln=True, fill=True)
    pdf.set_font("helvetica", "", 10)
    
    plan = extraction.get("action_plan", {})
    if isinstance(plan, str):
        try: plan = json.loads(plan)
        except: pass

    if isinstance(plan, dict):
        for step in plan.get("steps", []):
            pdf.multi_cell(0, 6, f"- {step}")
        pdf.ln(2)
        pdf.set_font("helvetica", "B", 10)
        pdf.cell(0, 6, f"Recommendation: {plan.get('recommendation', 'N/A')}", ln=True)
    else:
        pdf.cell(0, 6, str(plan), ln=True)
        
    pdf.ln(5)
    
    # Deadlines
    pdf.set_font("helvetica", "B", 11)
    pdf.cell(0, 8, " DEADLINES & COMPLIANCE", ln=True, fill=True)
    pdf.set_font("helvetica", "", 10)
    pdf.cell(0, 6, f"Compliance Deadline: {extraction.get('compliance_deadline', 'N/A')}", ln=True)
    pdf.cell(0, 6, f"Appeal Window: {extraction.get('appeal_window', 'N/A')}", ln=True)
    
    # Footer
    pdf.set_y(-30)
    pdf.set_font("helvetica", "I", 8)
    pdf.cell(0, 10, "Generated by LexFlow AI for Bharat Hackathon.", align="C")

    # Output to stream
    pdf_output = io.BytesIO()
    pdf_str = pdf.output(dest='S')
    pdf_output.write(pdf_str)
    pdf_output.seek(0)
    
    filename = f"LexFlow_ActionPlan_{extraction.get('case_number', 'export')}.pdf"
    return StreamingResponse(
        pdf_output,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

# ── Alerts Feed ───────────────────────────────────────────────────────────────
@router.get("/alerts")
async def get_dashboard_alerts(current_user: dict = Depends(require_admin_or_official)):
    """
    Return a feed of recent activity (newly verified or flagged cases).
    Used for the notification ticker.
    """
    db = get_db()
    
    alerts = []
    async for doc in db.cases.find({"status": {"$in": ["verified", "flagged"]}}).sort("created_at", -1).limit(50):
        data = dict(doc)
        status_msg = "verified and ready for action" if data.get("status") == "verified" else "flagged for review"
        alerts.append({
            "id": str(data.get("_id")),
            "case_number": data.get("case_number", "New Case"),
            "message": f"Case {data.get('case_number', 'Unknown')} was {status_msg}.",
            "status": data.get("status"),
            "created_at": data.get("created_at")
        })
        
    # Sort by timestamp desc and limit to 10
    alerts.sort(key=lambda x: x.get("created_at") if x.get("created_at") else datetime.min, reverse=True)
    alerts = alerts[:10]

    # Serialize timestamps
    for a in alerts:
        if a.get("created_at") and hasattr(a["created_at"], "isoformat"):
            a["timestamp"] = a["created_at"].isoformat()
        else:
            a["timestamp"] = None
        a.pop("created_at", None)

    return alerts
