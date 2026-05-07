"""
routes/cases.py
---------------
Handles PDF upload and case listing for LexFlow.
- POST /cases/upload  → save PDF file, create DB row, return case_id
- GET  /cases/        → list cases (filtered by role)
- GET  /cases/{id}    → single case detail
"""

from datetime import datetime

from bson import ObjectId
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from database import local_store
from database.mongo import get_db, get_fs, is_production_runtime
from auth.auth import get_current_user
from auth.roles import require_admin, require_student

router = APIRouter(prefix="/cases", tags=["Cases"])

# ── Upload PDF ────────────────────────────────────────────────────────────────
@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_case(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    """
    Upload a court judgment PDF into MongoDB GridFS and create a MongoDB case record.
    Returns the new case_id for downstream extraction.
    """
    filename = (file.filename or "").strip()
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    content = await file.read()

    try:
        db = get_db()
        fs = get_fs()
        file_id = await fs.upload_from_stream(filename, content, metadata={"contentType": "application/pdf"})
    except Exception as exc:
        if is_production_runtime():
            raise HTTPException(
                status_code=503,
                detail=f"Database storage is unavailable. Set MONGODB_URI in Render and redeploy. ({str(exc)})",
            )
        case_doc = local_store.create_case(filename, content, current_user["id"])
        return {
            "case_id": case_doc["id"],
            "pdf_url": case_doc["pdf_url"],
            "status": case_doc["status"],
            "message": "PDF uploaded locally. MongoDB storage is unavailable.",
        }

    case_doc = {
        "pdf_file_id": file_id,
        "pdf_url": f"/files/{str(file_id)}",
        "status": "pending",
        "uploaded_by": ObjectId(current_user["id"]),
        "created_at": datetime.utcnow(),
        "case_number": None,  # to be filled by extraction
    }

    try:
        res = await db.cases.insert_one(case_doc)
        case_id = str(res.inserted_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save to database: {str(e)}")

    return {
        "case_id": case_id,
        "pdf_url": case_doc["pdf_url"],
        "status": "pending",
        "message": "PDF uploaded successfully. Trigger /extract/{case_id} to start AI extraction.",
    }


# ── List Cases ────────────────────────────────────────────────────────────────
@router.get("/")
async def list_cases(current_user: dict = Depends(get_current_user)):
    """
    List cases from MongoDB based on role.
    Merges extraction data (parties, deadlines, etc.) into each case
    so the frontend gets complete info for display.
    """
    role = current_user["role"]

    # Students see ALL cases (admin uploads cases for students to study)
    # Officials only see verified cases
    # Admins see everything
    q: dict = {}
    if role == "official":
        q["status"] = "verified"
    # student and admin: no filter → see all cases

    results = []
    try:
        db = get_db()

        # Build a lookup of extraction data keyed by case_id
        extraction_map: dict = {}
        async for ext in db.extractions.find():
            ext_data = dict(ext)
            cid = ext_data.get("case_id")
            if cid:
                extraction_map[cid] = ext_data

        async for doc in db.cases.find(q).sort("created_at", -1):
            d = dict(doc)
            d["id"] = str(d.pop("_id"))
            if d.get("uploaded_by"):
                d["uploaded_by"] = str(d["uploaded_by"])
            if d.get("pdf_file_id"):
                d["pdf_file_id"] = str(d["pdf_file_id"])
            if d.get("created_at") and hasattr(d["created_at"], "isoformat"):
                d["created_at"] = d["created_at"].isoformat()

            # Merge extraction fields into the case so frontend gets full data
            ext = extraction_map.get(d["id"])
            if ext:
                for field in ("parties", "case_number", "date_of_order",
                              "key_directions", "compliance_deadline",
                              "appeal_window", "responsible_dept",
                              "action_plan", "source_references",
                              "confidence_score"):
                    if field in ext and (not d.get(field)):
                        d[field] = ext[field]
                # Also include urgency from action_plan
                if ext.get("action_plan") and isinstance(ext["action_plan"], dict):
                    d.setdefault("urgency", ext["action_plan"].get("urgency"))

            results.append(d)
    except Exception as exc:
        if is_production_runtime():
            raise HTTPException(
                status_code=503,
                detail=f"Database is unavailable. Set MONGODB_URI in Render and redeploy. ({str(exc)})",
            )
        results = []

    # Also include local-store cases (fallback when MongoDB is down)
    for case in local_store.cases.values():
        # Officials only see verified local cases
        if role == "official" and case.get("status") != "verified":
            continue
        serialized = local_store.serialize_case(case)
        # Merge local extraction data
        ext = local_store.extractions.get(case.get("id", ""))
        if ext:
            for field in ("parties", "case_number", "date_of_order",
                          "key_directions", "compliance_deadline",
                          "appeal_window", "responsible_dept",
                          "action_plan", "source_references",
                          "confidence_score"):
                if field in ext and (not serialized.get(field)):
                    serialized[field] = ext[field]
            if ext.get("action_plan") and isinstance(ext["action_plan"], dict):
                serialized.setdefault("urgency", ext["action_plan"].get("urgency"))
        results.append(serialized)

    return results


# ── Single Case ───────────────────────────────────────────────────────────────
@router.get("/{case_id}")
async def get_case(case_id: str, current_user: dict = Depends(get_current_user)):
    """Return a single case by ID from MongoDB, including its extraction if available."""
    local_case = local_store.cases.get(case_id)
    if local_case:
        return {
            "case": local_store.serialize_case(local_case),
            "extraction": local_store.serialize_extraction(local_store.extractions[case_id])
            if case_id in local_store.extractions else None,
        }

    db = get_db()
    try:
        oid = ObjectId(case_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid case id.")

    case_doc = await db.cases.find_one({"_id": oid})
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

    extraction_doc = await db.extractions.find_one({"case_id": case_data["id"]})
    extraction_data = None
    if extraction_doc:
        extraction_data = dict(extraction_doc)
        extraction_data["id"] = str(extraction_data.pop("_id"))
        extraction_data.pop("case_id", None)
        if extraction_data.get("created_at") and hasattr(extraction_data["created_at"], "isoformat"):
            extraction_data["created_at"] = extraction_data["created_at"].isoformat()

    return {"case": case_data, "extraction": extraction_data}
