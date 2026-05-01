"""
routes/cases.py
---------------
Handles PDF upload and case listing for LexFlow.
- POST /cases/upload  → save PDF file, create DB row, return case_id
- GET  /cases/        → list cases (filtered by role)
- GET  /cases/{id}    → single case detail
"""

import os
import uuid
from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
import aiofiles

from database.db import get_connection
from auth.auth import get_current_user
from auth.roles import require_admin, require_student

router = APIRouter(prefix="/cases", tags=["Cases"])

# Directory where uploaded PDFs are stored
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


# ── Upload PDF ────────────────────────────────────────────────────────────────
@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_case(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    """
    Upload a court judgment PDF.
    Saves file to disk, inserts a 'cases' row with status='pending'.
    Returns the new case_id for downstream extraction.
    """
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    # Generate unique filename to avoid collisions
    unique_name = f"{uuid.uuid4().hex}_{file.filename}"
    save_path = os.path.join(UPLOAD_DIR, unique_name)

    # Write file to disk asynchronously
    async with aiofiles.open(save_path, "wb") as out_file:
        content = await file.read()
        await out_file.write(content)

    # Insert into DB
    conn = get_connection()
    cursor = conn.execute(
        """
        INSERT INTO cases (pdf_path, status, uploaded_by)
        VALUES (?, 'pending', ?)
        """,
        (save_path, current_user["id"]),
    )
    case_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return {
        "case_id": case_id,
        "pdf_path": save_path,
        "status": "pending",
        "message": "PDF uploaded successfully. Trigger /extract/{case_id} to start AI extraction.",
    }


# ── List Cases ────────────────────────────────────────────────────────────────
@router.get("/")
def list_cases(current_user: dict = Depends(get_current_user)):
    """
    List cases based on role:
    - admin   → all cases
    - student → only cases they uploaded
    - official → only verified cases
    """
    conn = get_connection()
    role = current_user["role"]

    if role == "admin":
        rows = conn.execute("SELECT * FROM cases ORDER BY created_at DESC").fetchall()
    elif role == "student":
        rows = conn.execute(
            "SELECT * FROM cases WHERE uploaded_by = ? ORDER BY created_at DESC",
            (current_user["id"],),
        ).fetchall()
    else:  # official
        rows = conn.execute(
            "SELECT * FROM cases WHERE status = 'verified' ORDER BY created_at DESC"
        ).fetchall()

    conn.close()
    return [dict(r) for r in rows]


# ── Single Case ───────────────────────────────────────────────────────────────
@router.get("/{case_id}")
def get_case(case_id: int, current_user: dict = Depends(get_current_user)):
    """Return a single case by ID, including its extraction if available."""
    conn = get_connection()
    case = conn.execute(
        "SELECT * FROM cases WHERE id = ?", (case_id,)
    ).fetchone()

    if not case:
        conn.close()
        raise HTTPException(status_code=404, detail="Case not found.")

    extraction = conn.execute(
        "SELECT * FROM extractions WHERE case_id = ?", (case_id,)
    ).fetchone()
    conn.close()

    return {
        "case": dict(case),
        "extraction": dict(extraction) if extraction else None,
    }
