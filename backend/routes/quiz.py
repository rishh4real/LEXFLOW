"""
routes/quiz.py
--------------
Quiz engine routes for law students.
- GET  /quiz/{case_id}           → return 5 questions (NO correct answers)
- POST /quiz/{case_id}/submit    → accept student answers, return match score
- GET  /quiz/{case_id}/result    → return previous submission result (with AI answers revealed)
Phase 1: mock questions. Phase 5: real quiz generation from extractions.
"""

import json
from datetime import datetime

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from database.mongo import get_db
from auth.auth import get_current_user
from auth.roles import require_student
from services.confidence import score_answers

router = APIRouter(prefix="/quiz", tags=["Quiz"])


# ── Request body schema ───────────────────────────────────────────────────────
class SubmitAnswers(BaseModel):
    answers: dict[str, str]  # { question_id: student_answer_text }


# ── Get Questions ─────────────────────────────────────────────────────────────
@router.get("/{case_id}")
async def get_questions(case_id: str, current_user: dict = Depends(get_current_user)):
    """
    Return the 5 quiz questions for a case from MongoDB.
    IMPORTANT: correct_answer is NEVER included in this response.
    """
    db = get_db()
    try:
        case_oid = ObjectId(case_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid case id.")

    case_doc = await db.cases.find_one({"_id": case_oid})
    if not case_doc:
        raise HTTPException(status_code=404, detail="Case not found.")
    
    results = []
    async for doc in db.quiz_questions.find({"case_id": case_id}).sort("question_order", 1):
        d = dict(doc)
        results.append({
            "id": str(d.get("_id")),
            "question_order": d["question_order"],
            "question_text": d["question_text"]
        })

    return results


# ── Submit Answers ────────────────────────────────────────────────────────────
@router.post("/{case_id}/submit")
async def submit_answers(
    case_id: str,
    body: SubmitAnswers,
    current_user: dict = Depends(get_current_user),
):
    """
    Accept student answers for a case quiz and store in MongoDB.
    Uses confidence.py fuzzy matching.
    Returns match_score (0-100) and per-question breakdown.
    """
    db = get_db()
    student_oid = ObjectId(current_user["id"])

    # Prevent duplicate submissions
    existing = await db.quiz_submissions.find_one({"case_id": case_id, "student_id": student_oid})
    if existing:
        raise HTTPException(status_code=400, detail="Quiz already submitted for this case.")

    # Fetch correct AI answers
    questions = []
    async for q in db.quiz_questions.find({"case_id": case_id}):
        questions.append(dict(q))
    if not questions:
        raise HTTPException(status_code=400, detail="No questions found for this case.")

    ai_answers = {str(q["_id"]): q.get("correct_answer", "") for q in questions}

    # Score answers
    scoring_result = score_answers(body.answers, ai_answers)
    match_score = scoring_result["match_score"]
    submission_status = scoring_result["status"]
    breakdown = scoring_result["breakdown"]

    # Save submission
    submission_data = {
        "case_id": case_id,
        "student_id": student_oid,
        "answers": body.answers,
        "match_score": match_score,
        "status": submission_status,
        "submitted_at": datetime.utcnow(),
    }

    try:
        await db.quiz_submissions.insert_one(submission_data)

        # If flagged, update case status to 'flagged' (needs official review)
        # If score is high, and no existing 'verified' status, we might keep 'pending' 
        # but here we update status based on student performance if it indicates discrepancy.
        if submission_status == "flagged":
            await db.cases.update_one({"_id": ObjectId(case_id)}, {"$set": {"status": "flagged"}})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save submission: {str(e)}")

    return {
        "match_score": round(match_score, 1),
        "status": submission_status,
        "breakdown": breakdown,
        "message": "Answers submitted successfully.",
    }


# ── Get Result (reveals AI answers post-submission) ───────────────────────────
@router.get("/{case_id}/result")
async def get_result(case_id: str, current_user: dict = Depends(get_current_user)):
    """
    Return quiz result from MongoDB after submission, including AI correct answers.
    """
    db = get_db()
    student_oid = ObjectId(current_user["id"])

    submission = await db.quiz_submissions.find_one(
        {"case_id": case_id, "student_id": student_oid},
        sort=[("submitted_at", -1)],
    )
    if not submission:
        raise HTTPException(
            status_code=404, detail="No submission found. Submit your answers first."
        )
    
    submission_out = dict(submission)
    submission_out["id"] = str(submission_out.pop("_id"))
    submission_out["student_id"] = str(submission_out["student_id"])
    if submission_out.get("submitted_at") and hasattr(submission_out["submitted_at"], "isoformat"):
        submission_out["submitted_at"] = submission_out["submitted_at"].isoformat()

    # Reveal AI answers
    ai_answers = {}
    async for q in db.quiz_questions.find({"case_id": case_id}):
        ai_answers[str(q["_id"])] = q.get("correct_answer", "")
    submission_out["ai_answers"] = ai_answers

    return submission_out
