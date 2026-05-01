"""
services/confidence.py
Fuzzy string matching between student answers and AI answers.
Score >= 80 = approved, < 80 = flagged.
"""
from thefuzz import fuzz

def score_answers(student_answers: dict, ai_answers: dict) -> dict:
    """
    Compare student answers to AI answers field by field.
    Returns overall match_score and per-question breakdown.
    student_answers: {question_id: student_text}
    ai_answers:      {question_id: correct_text}
    """
    scores = []
    breakdown = []
    for q_id, correct in ai_answers.items():
        student = student_answers.get(str(q_id), student_answers.get(q_id, ""))
        ratio = fuzz.token_sort_ratio(str(student).lower(), str(correct).lower())
        scores.append(ratio)
        breakdown.append({
            "question_id": q_id,
            "student_answer": student,
            "ai_answer": correct,
            "score": ratio,
            "match": ratio >= 80,
        })
    overall = sum(scores) / len(scores) if scores else 0
    return {
        "match_score": round(overall, 1),
        "status": "approved" if overall >= 80 else "flagged",
        "breakdown": breakdown,
    }
