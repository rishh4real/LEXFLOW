"""
routes/verification.py
----------------------
Admin verification workflow for flagged cases.
- GET  /verify/flagged          → list all flagged cases for admin review
- POST /verify/{case_id}        → admin approves, rejects, or edits a case
- GET  /verify/{case_id}/detail → side-by-side AI vs student comparison for admin
"""

import json
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from bson import ObjectId

from database import local_store
from database.mongo import get_db
from auth.auth import get_current_user
from auth.roles import require_admin

router = APIRouter(prefix="/verify", tags=["Verification"])


# ── Request body ──────────────────────────────────────────────────────────────
class VerificationAction(BaseModel):
    action: str               # "approve" | "reject" | "flag"
    notes: Optional[str] = None


# ── List Flagged Cases ────────────────────────────────────────────────────────
@router.get("/flagged")
async def list_flagged(current_user: dict = Depends(require_admin)):
    """
    Return all cases with status='flagged' from MongoDB.
    Includes the latest quiz submission scores for context.
    """
    results = []
    try:
        db = get_db()
        async for doc in db.cases.find({"status": "flagged"}).sort("created_at", -1):
            case_data = dict(doc)
            case_id = str(case_data.pop("_id"))
            case_data["id"] = case_id
            if case_data.get("uploaded_by"):
                case_data["uploaded_by"] = str(case_data["uploaded_by"])
            if case_data.get("pdf_file_id"):
                case_data["pdf_file_id"] = str(case_data["pdf_file_id"])

            extraction_doc = await db.extractions.find_one({"case_id": case_id})
            if extraction_doc:
                extraction_data = dict(extraction_doc)
                extraction_data.pop("_id", None)
                extraction_data.pop("case_id", None)
                for field in (
                    "case_number", "parties", "date_of_order", "key_directions",
                    "compliance_deadline", "appeal_window", "responsible_dept",
                    "action_plan", "source_references", "confidence_score",
                ):
                    if field in extraction_data and not case_data.get(field):
                        case_data[field] = extraction_data[field]
            
            # Fetch latest submission for this case
            sub_data = await db.quiz_submissions.find_one(
                {"case_id": case_id},
                sort=[("submitted_at", -1)],
            )
            
            if sub_data:
                sub_out = dict(sub_data)
                sub_out["id"] = str(sub_out.pop("_id"))
                sub_out["student_id"] = str(sub_out["student_id"])
                if sub_out.get("submitted_at") and hasattr(sub_out["submitted_at"], "isoformat"):
                    sub_out["submitted_at"] = sub_out["submitted_at"].isoformat()
                case_data["submission"] = sub_out
                case_data["match_score"] = sub_out["match_score"]
                case_data["submitted_at"] = sub_data["submitted_at"].isoformat() if sub_data.get("submitted_at") else None
                
                # Fetch student info
                student = await db.users.find_one({"_id": sub_data["student_id"]})
                if student:
                    case_data["student_name"] = student.get("name")
                    case_data["student_email"] = student.get("email")

            questions = []
            async for q_doc in db.quiz_questions.find({"case_id": case_id}).sort("question_order", 1):
                q_data = dict(q_doc)
                q_data["id"] = str(q_data.pop("_id"))
                q_data.pop("case_id", None)
                questions.append(q_data)
            case_data["questions"] = questions

            if case_data.get("created_at") and hasattr(case_data["created_at"], "isoformat"):
                case_data["created_at"] = case_data["created_at"].isoformat()
                
            results.append(case_data)
    except Exception:
        pass

    for case in local_store.cases.values():
        if case.get("status") == "flagged":
            case_data = local_store.serialize_case(case)
            case_data.update(local_store.serialize_extraction(local_store.extractions.get(case["id"], {})))
            # Resolve uploader info — local cases are always admin-uploaded
            uploader_id = case.get("uploaded_by")
            uploader = local_store.users.get(uploader_id) if uploader_id else None
            submission = local_store.latest_submission(case["id"])
            if submission:
                student = local_store.users.get(submission.get("student_id"), {})
                case_data["student_name"] = student.get("name", "Student submission")
                case_data["student_email"] = student.get("email")
                case_data["match_score"] = submission.get("match_score", 0)
                case_data["submitted_at"] = local_store.serialize_submission(submission).get("submitted_at")
                case_data["submission"] = local_store.serialize_submission(submission)
            else:
                case_data["student_name"] = "Awaiting student"
                case_data["match_score"] = 0
            case_data["uploaded_by_name"] = uploader.get("name", "Admin") if uploader else "Admin"
            case_data["uploaded_by_role"] = uploader.get("role", "admin") if uploader else "admin"
            case_data["questions"] = local_store.questions.get(case["id"], [])
            results.append(case_data)

    return results


# ── Side-by-side Comparison Detail ───────────────────────────────────────────
@router.get("/{case_id}/detail")
async def verification_detail(case_id: str, current_user: dict = Depends(require_admin)):
    """
    Return AI extraction answers alongside student answers for comparison from MongoDB.
    """
    if case_id in local_store.cases:
        case = local_store.cases[case_id]
        return {
            "case": local_store.serialize_case(case),
            "extraction": local_store.serialize_extraction(local_store.extractions[case_id])
            if case_id in local_store.extractions else None,
            "submission": local_store.serialize_submission(local_store.latest_submission(case_id))
            if local_store.latest_submission(case_id) else None,
            "questions": local_store.public_questions(case_id),
        }

    db = get_db()
    try:
        case_oid = ObjectId(case_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid case id.")

    case_doc = await db.cases.find_one({"_id": case_oid})
    if not case_doc:
        raise HTTPException(status_code=404, detail="Case not found.")

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

    submission_doc = await db.quiz_submissions.find_one({"case_id": case_id}, sort=[("submitted_at", -1)])
    submission_data = None
    if submission_doc:
        submission_data = dict(submission_doc)
        submission_data["id"] = str(submission_data.pop("_id"))
        submission_data["student_id"] = str(submission_data["student_id"])
        if submission_data.get("submitted_at") and hasattr(submission_data["submitted_at"], "isoformat"):
            submission_data["submitted_at"] = submission_data["submitted_at"].isoformat()

        student = await db.users.find_one({"_id": ObjectId(submission_data["student_id"])})
        if student:
            submission_data["name"] = student.get("name")
            submission_data["email"] = student.get("email")

    questions = []
    async for q_doc in db.quiz_questions.find({"case_id": case_id}).sort("question_order", 1):
        q_data = dict(q_doc)
        q_data["id"] = str(q_data.pop("_id"))
        q_data.pop("case_id", None)
        questions.append(q_data)

    return {
        "case": case_data,
        "extraction": extraction_data,
        "submission": submission_data,
        "questions": questions,
    }


# ── Admin Decision ────────────────────────────────────────────────────────────
@router.post("/{case_id}")
async def verify_case(
    case_id: str,
    body: VerificationAction,
    current_user: dict = Depends(require_admin),
):
    """
    Admin approves, rejects, or re-flags a case in MongoDB.
    """
    if body.action not in ("approve", "reject", "flag"):
        raise HTTPException(status_code=400, detail="Action must be approve, reject, or flag.")

    if case_id in local_store.cases:
        new_status = {
            "approve": "verified",
            "reject": "flagged",
            "flag": "flagged",
        }[body.action]
        local_store.cases[case_id]["status"] = new_status
        local_store._save()
        return {
            "message": f"Case {body.action}d successfully.",
            "case_id": case_id,
            "new_status": new_status,
        }

    db = get_db()
    try:
        case_oid = ObjectId(case_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid case id.")

    case_doc = await db.cases.find_one({"_id": case_oid})
    if not case_doc:
        raise HTTPException(status_code=404, detail="Case not found.")

    # Determine new case status
    new_status = {
        "approve": "verified",
        "reject": "flagged",
        "flag": "flagged",
    }[body.action]

    try:
        await db.cases.update_one({"_id": case_oid}, {"$set": {"status": new_status}})

        verification_data = {
            "case_id": case_id,
            "status": body.action,
            "reviewed_by": ObjectId(current_user["id"]),
            "notes": body.notes,
            "created_at": datetime.utcnow(),
        }
        await db.verifications.insert_one(verification_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update verification: {str(e)}")

    return {
        "message": f"Case {body.action}d successfully.",
        "case_id": case_id,
        "new_status": new_status,
    }
