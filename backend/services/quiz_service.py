"""
services/quiz_service.py
Generate 5 quiz questions from extraction data. Store AI answers in DB (never sent pre-submission).
"""
from datetime import datetime

from database.mongo import get_db

def build_question_prompts(extraction: dict) -> list[str]:
    """Build case-specific prompts so two uploaded cases do not show as one generic quiz."""
    case_label = extraction.get("case_number") or "this judgment"
    parties = extraction.get("parties")
    context = f"{case_label}"
    if parties:
        context = f"{case_label} ({parties})"

    return [
        f"For {context}, what is the final order: compliance or dismissed?",
        f"For {context}, which department or authority must act?",
        f"For {context}, what compliance deadline is mentioned in the judgment?",
        f"For {context}, is there a limitation period for appeal? If yes, what is it?",
        f"For {context}, what is the key court directive in one line?",
    ]

async def generate_questions(case_id: str, extraction: dict) -> list:
    """Map extraction fields to 5 fixed questions and store with AI answers in MongoDB."""
    db = get_db()
    prompts = build_question_prompts(extraction)
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
    for i, (q, a) in enumerate(zip(prompts, ai_answers)):
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
