"""
routes/extraction.py
--------------------
Triggers AI extraction for a given case.
- POST /extract/{case_id}  → run PDF parser + Claude AI, store in extractions table
- GET  /extract/{case_id}  → return stored extraction result
Phase 1: returns mock data. Phase 4: connects real Claude API.
"""

from datetime import datetime

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException

from database import local_store
from database.mongo import get_db, get_fs
from auth.auth import get_current_user

router = APIRouter(prefix="/extract", tags=["Extraction"])

from services.pdf_parser import parse_pdf_bytes
from services.llm_service import extract_case
from services.quiz_service import generate_questions

# ── Trigger Extraction ────────────────────────────────────────────────────────
@router.post("/{case_id}")
async def trigger_extraction(case_id: str, current_user: dict = Depends(get_current_user)):
    """
    Trigger AI extraction for a case in MongoDB.
    Calls llm_service.extract_case() with real PDF text.
    """
    local_case = local_store.cases.get(case_id)
    if local_case:
        if case_id in local_store.extractions:
            if not local_store.public_questions(case_id):
                local_store.create_questions(case_id, local_store.extractions[case_id])
            return {"message": "Extraction already exists.", "case_id": case_id}

        raw_text = ""
        try:
            pdf_data = parse_pdf_bytes(open(local_case["pdf_path"], "rb").read())
            raw_text = pdf_data.get("full_text", "")
        except Exception:
            raw_text = ""

        try:
            result = extract_case(raw_text) if len(raw_text.strip()) >= 50 else {}
        except Exception:
            result = {}

        if result:
            extraction_data = {
                "case_id": case_id,
                "case_number": result.get("case_number") or local_case["case_number"],
                "parties": result.get("parties") or "Parties pending extraction",
                "date_of_order": result.get("date_of_order"),
                "key_directions": result.get("key_directions"),
                "compliance_deadline": result.get("compliance_deadline"),
                "appeal_window": result.get("appeal_window"),
                "responsible_dept": result.get("responsible_department"),
                "action_plan": result.get("action_plan"),
                "source_references": result.get("source_references"),
                "confidence_score": result.get("confidence_score", 0.90),
                "created_at": datetime.utcnow(),
            }
            local_store.extractions[case_id] = extraction_data
            local_case.update({"case_number": extraction_data["case_number"], "status": "pending"})
        else:
            extraction_data = local_store.build_fallback_extraction(case_id, raw_text)

        local_store.create_questions(case_id, extraction_data)

        return {
            "message": "Extraction complete.",
            "case_id": case_id,
            "data": local_store.serialize_extraction(extraction_data),
        }

    db = get_db()
    fs = get_fs()
    try:
        case_oid = ObjectId(case_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid case id.")

    case_doc = await db.cases.find_one({"_id": case_oid})
    if not case_doc:
        raise HTTPException(status_code=404, detail="Case not found.")

    # Check if already extracted
    existing = await db.extractions.find_one({"case_id": case_id})
    if existing:
        return {"message": "Extraction already exists.", "case_id": case_id}

    # Download PDF bytes from GridFS and extract text
    try:
        pdf_file_id = case_doc.get("pdf_file_id")
        if not pdf_file_id:
            raise Exception("Case has no pdf_file_id")
        grid_out = await fs.open_download_stream(pdf_file_id)
        pdf_bytes = await grid_out.read()
        pdf_data = parse_pdf_bytes(pdf_bytes)
        raw_text = pdf_data.get("full_text", "")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF Parsing failed: {str(e)}")

    if len(raw_text.strip()) < 50:
        raise HTTPException(status_code=400, detail="Could not extract enough text from PDF.")

    # Call LLM
    try:
        result = extract_case(raw_text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI extraction failed: {str(e)}")

    result.setdefault("confidence_score", 0.90)

    try:
        extraction_data = {
            "case_id": case_id,
            "case_number": result["case_number"],
            "parties": result["parties"],
            "date_of_order": result["date_of_order"],
            "key_directions": result["key_directions"],
            "compliance_deadline": result["compliance_deadline"],
            "appeal_window": result["appeal_window"],
            "responsible_dept": result["responsible_department"],
            "action_plan": result["action_plan"],
            "source_references": result["source_references"],
            "confidence_score": result["confidence_score"],
            "created_at": datetime.utcnow(),
        }

        await db.extractions.insert_one(extraction_data)

        # Update case record with number and status
        await db.cases.update_one(
            {"_id": case_oid},
            {"$set": {"case_number": result["case_number"], "status": "pending"}},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to store extraction: {str(e)}")

    # Generate Quiz questions based on this new extraction
    await generate_questions(case_id, extraction_data)

    return {"message": "Extraction complete.", "case_id": case_id, "data": result}


# ── Get Extraction ────────────────────────────────────────────────────────────
@router.get("/{case_id}")
async def get_extraction(case_id: str, current_user: dict = Depends(get_current_user)):
    """Return stored extraction data for a case from MongoDB."""
    if case_id in local_store.extractions:
        return local_store.serialize_extraction(local_store.extractions[case_id])

    db = get_db()
    doc = await db.extractions.find_one({"case_id": case_id})
    if not doc:
        raise HTTPException(status_code=404, detail="No extraction found for this case.")

    result = dict(doc)
    result["id"] = str(result.pop("_id"))
    if result.get("created_at") and hasattr(result["created_at"], "isoformat"):
        result["created_at"] = result["created_at"].isoformat()
    return result
