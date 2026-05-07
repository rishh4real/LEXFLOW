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

from database import local_store
from database.mongo import get_db
from auth.auth import get_current_user
from auth.roles import require_student
from services.confidence import score_answers
from services.quiz_service import generate_questions

router = APIRouter(prefix="/quiz", tags=["Quiz"])


# ── Request body schema ───────────────────────────────────────────────────────
class SubmitAnswers(BaseModel):
    answers: dict[str, str]  # { question_id: student_answer_text }


def has_generic_questions(questions: list[dict]) -> bool:
    if not questions:
        return False
    return any(
        not (q.get("question_text") or "").startswith("For ")
        for q in questions
    )


# ── Get Questions ─────────────────────────────────────────────────────────────
@router.get("/{case_id}")
async def get_questions(case_id: str, current_user: dict = Depends(get_current_user)):
    """
    Return the 5 quiz questions for a case from MongoDB.
    IMPORTANT: correct_answer is NEVER included in this response.
    """
    if case_id in local_store.cases:
        questions = local_store.public_questions(case_id)
        if (not questions or has_generic_questions(questions)) and case_id in local_store.extractions:
            questions = local_store.create_questions(case_id, local_store.extractions[case_id])
        return questions

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

    if not results or has_generic_questions(results):
        extraction_doc = await db.extractions.find_one({"case_id": case_id})
        if extraction_doc:
            extraction_data = dict(extraction_doc)
            extraction_data.pop("_id", None)
            results = await generate_questions(case_id, extraction_data)

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
    if case_id in local_store.cases:
        student_id = current_user["id"]
        if local_store.submission_for(case_id, student_id):
            raise HTTPException(status_code=400, detail="Quiz already submitted for this case.")

        questions = local_store.questions.get(case_id, [])
        if not questions:
            raise HTTPException(status_code=400, detail="No questions found for this case.")

        ai_answers = {q["id"]: q.get("correct_answer", "") for q in questions}
        scoring_result = score_answers(body.answers, ai_answers)
        submission = local_store.save_submission(case_id, student_id, body.answers, scoring_result)

        return {
            "match_score": round(scoring_result["match_score"], 1),
            "status": scoring_result["status"],
            "breakdown": scoring_result["breakdown"],
            "ai_answers": ai_answers,
            "message": "Answers submitted successfully.",
            "submission": local_store.serialize_submission(submission),
        }

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
    if case_id in local_store.cases:
        submission = local_store.submission_for(case_id, current_user["id"])
        if not submission:
            raise HTTPException(
                status_code=404, detail="No submission found. Submit your answers first."
            )
        result = local_store.serialize_submission(submission)
        result["ai_answers"] = {
            q["id"]: q.get("correct_answer", "")
            for q in local_store.questions.get(case_id, [])
        }
        return result

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
