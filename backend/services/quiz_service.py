"""
services/quiz_service.py
Generate 5 quiz questions from extraction data. Store AI answers in DB (never sent pre-submission).
"""
from datetime import datetime

from database.mongo import get_db

QUESTIONS = [
    "What is the final order — compliance or dismissed?",
    "Which department or authority must act?",
    "What is the compliance deadline mentioned in the judgment?",
    "Is there a limitation period for appeal? If yes, what is it?",
    "What is the key directive of the court in one line?",
]

async def generate_questions(case_id: str, extraction: dict) -> list:
    """Map extraction fields to 5 fixed questions and store with AI answers in MongoDB."""
    db = get_db()
    ai_answers = [
        extraction.get("action_plan", {}).get("recommendation", ""),
        extraction.get("responsible_dept", ""),
        extraction.get("compliance_deadline", ""),
        extraction.get("appeal_window", ""),
        extraction.get("key_directions", ""),
    ]

    # Replace old questions for this case
    await db.quiz_questions.delete_many({"case_id": case_id})

    docs = []
    stored = []
    now = datetime.utcnow()
    for i, (q, a) in enumerate(zip(QUESTIONS, ai_answers)):
        docs.append(
            {
                "case_id": case_id,
                "question_text": q,
                "correct_answer": a,
                "question_order": i + 1,
                "created_at": now,
            }
        )

    if docs:
        res = await db.quiz_questions.insert_many(docs)
        for oid, doc in zip(res.inserted_ids, docs):
            stored.append({"id": str(oid), "question_order": doc["question_order"], "question_text": doc["question_text"]})

    return stored
