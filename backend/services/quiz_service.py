"""
services/quiz_service.py
Generate 5 quiz questions from extraction data. Store AI answers in DB (never sent pre-submission).
"""
import json
from database.db import get_connection

QUESTIONS = [
    "What is the final order — compliance or dismissed?",
    "Which department or authority must act?",
    "What is the compliance deadline mentioned in the judgment?",
    "Is there a limitation period for appeal? If yes, what is it?",
    "What is the key directive of the court in one line?",
]

def generate_questions(case_id: int, extraction: dict) -> list:
    """Map extraction fields to 5 fixed questions and store with AI answers."""
    ai_answers = [
        extraction.get("action_plan", {}).get("recommendation", ""),
        extraction.get("responsible_department", ""),
        extraction.get("compliance_deadline", ""),
        extraction.get("appeal_window", ""),
        extraction.get("key_directions", ""),
    ]
    conn = get_connection()
    # Clear old questions for this case
    conn.execute("DELETE FROM quiz_questions WHERE case_id = ?", (case_id,))
    stored = []
    for i, (q, a) in enumerate(zip(QUESTIONS, ai_answers)):
        cursor = conn.execute(
            "INSERT INTO quiz_questions (case_id, question_text, correct_answer, question_order) VALUES (?,?,?,?)",
            (case_id, q, a, i+1)
        )
        stored.append({"id": cursor.lastrowid, "question_order": i+1, "question_text": q})
    conn.commit()
    conn.close()
    return stored
