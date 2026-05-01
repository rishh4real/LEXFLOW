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
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from database.db import get_connection
from auth.auth import get_current_user
from auth.roles import require_student

router = APIRouter(prefix="/quiz", tags=["Quiz"])


# ── Mock questions (Phase 1 placeholder) ──────────────────────────────────────
MOCK_QUESTIONS = [
    {
        "id": 1,
        "question_order": 1,
        "question_text": "What is the final order — compliance or dismissed?",
    },
    {
        "id": 2,
        "question_order": 2,
        "question_text": "Which department or authority must act?",
    },
    {
        "id": 3,
        "question_order": 3,
        "question_text": "What is the compliance deadline mentioned in the judgment?",
    },
    {
        "id": 4,
        "question_order": 4,
        "question_text": "Is there a limitation period for appeal? If yes, what is it?",
    },
    {
        "id": 5,
        "question_order": 5,
        "question_text": "What is the key directive of the court in one line?",
    },
]

MOCK_ANSWERS = {
    1: "Compliance — respondent must act",
    2: "Public Works Department, Maharashtra",
    3: "90 days from date of order (2025-02-15)",
    4: "Yes, 30 days from date of order",
    5: "Install potable water supply in village XYZ within 90 days",
}


# ── Request body schema ───────────────────────────────────────────────────────
class SubmitAnswers(BaseModel):
    answers: dict[int, str]  # { question_id: student_answer_text }


# ── Get Questions ─────────────────────────────────────────────────────────────
@router.get("/{case_id}")
def get_questions(case_id: int, current_user: dict = Depends(get_current_user)):
    """
    Return the 5 quiz questions for a case.
    IMPORTANT: correct_answer is NEVER included in this response.
    Phase 1 returns mock questions; Phase 5 returns from DB.
    """
    conn = get_connection()

    # Check case exists
    case = conn.execute("SELECT id FROM cases WHERE id = ?", (case_id,)).fetchone()
    if not case:
        conn.close()
        raise HTTPException(status_code=404, detail="Case not found.")

    # Try to fetch real questions from DB first
    rows = conn.execute(
        """
        SELECT id, question_order, question_text
        FROM quiz_questions
        WHERE case_id = ?
        ORDER BY question_order
        """,
        (case_id,),
    ).fetchall()
    conn.close()

    if rows:
        return [dict(r) for r in rows]

    # Phase 1: return mock questions
    return MOCK_QUESTIONS


# ── Submit Answers ────────────────────────────────────────────────────────────
@router.post("/{case_id}/submit")
def submit_answers(
    case_id: int,
    body: SubmitAnswers,
    current_user: dict = Depends(get_current_user),
):
    """
    Accept student answers for a case quiz.
    Phase 1: compare against mock answers with simple exact match.
    Phase 5: use confidence.py fuzzy matching.
    Returns match_score (0-100) and per-question breakdown.
    """
    conn = get_connection()

    # Prevent duplicate submissions
    existing = conn.execute(
        "SELECT id FROM quiz_submissions WHERE case_id = ? AND student_id = ?",
        (case_id, current_user["id"]),
    ).fetchone()
    if existing:
        conn.close()
        raise HTTPException(status_code=400, detail="Quiz already submitted for this case.")

    # ── Phase 1 mock scoring ──────────────────────────────────────────────────
    correct = 0
    breakdown = []
    for q_id, student_ans in body.answers.items():
        ai_ans = MOCK_ANSWERS.get(int(q_id), "")
        # Simple case-insensitive match for Phase 1
        is_match = student_ans.strip().lower() == ai_ans.lower()
        if is_match:
            correct += 1
        breakdown.append({
            "question_id": q_id,
            "student_answer": student_ans,
            "match": is_match,
        })

    match_score = (correct / len(MOCK_ANSWERS)) * 100
    submission_status = "approved" if match_score >= 80 else "flagged"

    # Save submission
    conn.execute(
        """
        INSERT INTO quiz_submissions (case_id, student_id, answers_json, match_score, status)
        VALUES (?, ?, ?, ?, ?)
        """,
        (case_id, current_user["id"], json.dumps(body.answers), match_score, submission_status),
    )

    # If flagged, update case status
    if submission_status == "flagged":
        conn.execute(
            "UPDATE cases SET status = 'flagged' WHERE id = ?", (case_id,)
        )

    conn.commit()
    conn.close()

    return {
        "match_score": round(match_score, 1),
        "status": submission_status,
        "breakdown": breakdown,
        "message": "Answers submitted successfully.",
    }


# ── Get Result (reveals AI answers post-submission) ───────────────────────────
@router.get("/{case_id}/result")
def get_result(case_id: int, current_user: dict = Depends(get_current_user)):
    """
    Return quiz result after submission, including AI correct answers.
    Only available after the student has submitted answers.
    """
    conn = get_connection()
    submission = conn.execute(
        """
        SELECT * FROM quiz_submissions
        WHERE case_id = ? AND student_id = ?
        ORDER BY submitted_at DESC LIMIT 1
        """,
        (case_id, current_user["id"]),
    ).fetchone()
    conn.close()

    if not submission:
        raise HTTPException(
            status_code=404, detail="No submission found. Submit your answers first."
        )

    result = dict(submission)
    result["answers"] = json.loads(result["answers_json"])
    # Now reveal AI answers
    result["ai_answers"] = MOCK_ANSWERS

    return result
