"""
database/local_store.py
-----------------------
Disk-persisted fallback for local development when MongoDB is unavailable.
Data is saved to a JSON file so uploads survive server restarts.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4

UPLOAD_DIR = Path(__file__).resolve().parents[1] / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

_STORE_FILE = UPLOAD_DIR / "_local_store.json"

cases: dict[str, dict] = {}
extractions: dict[str, dict] = {}
questions: dict[str, list[dict]] = {}
submissions: dict[str, dict] = {}
users: dict[str, dict] = {
    "000000000000000000000001": {"name": "Admin User", "email": "admin@lexflow.com", "role": "admin"},
    "000000000000000000000002": {"name": "Law Student", "email": "student@lexflow.com", "role": "student"},
    "000000000000000000000003": {"name": "Govt Official", "email": "official@lexflow.com", "role": "official"},
}


# ── Persistence helpers ───────────────────────────────────────────────────────
def _save():
    """Flush current state to disk as JSON."""
    try:
        payload = {
            "cases": {k: _jsonable(v) for k, v in cases.items()},
            "extractions": {k: _jsonable(v) for k, v in extractions.items()},
            "questions": {
                k: [_jsonable(item) for item in v]
                for k, v in questions.items()
            },
            "submissions": {k: _jsonable(v) for k, v in submissions.items()},
        }
        _STORE_FILE.write_text(json.dumps(payload, default=str), encoding="utf-8")
    except Exception as exc:
        print(f"⚠️  local_store: failed to persist – {exc}")


def _load():
    """Load persisted state from disk on startup."""
    global cases, extractions, questions, submissions
    if not _STORE_FILE.exists():
        return
    try:
        raw = json.loads(_STORE_FILE.read_text(encoding="utf-8"))
        cases = raw.get("cases", {})
        extractions = raw.get("extractions", {})
        questions = raw.get("questions", {})
        submissions = raw.get("submissions", {})
        print(f"✅  local_store: restored {len(cases)} cases, {len(extractions)} extractions from disk")
    except Exception as exc:
        print(f"⚠️  local_store: failed to load – {exc}")


def _jsonable(d: dict) -> dict:
    """Return a JSON-safe shallow copy (datetime → isoformat string)."""
    out = {}
    for k, v in d.items():
        if isinstance(v, datetime):
            out[k] = v.isoformat()
        else:
            out[k] = v
    return out


# Restore on import
_load()


def serialize_case(case: dict) -> dict:
    data = dict(case)
    created_at = data.get("created_at")
    if created_at and hasattr(created_at, "isoformat"):
        data["created_at"] = created_at.isoformat()
    return data


def create_case(filename: str, content: bytes, uploaded_by: str) -> dict:
    case_id = uuid4().hex
    safe_name = f"{case_id}_{Path(filename).name}"
    path = UPLOAD_DIR / safe_name
    path.write_bytes(content)

    case = {
        "id": case_id,
        "pdf_path": str(path),
        "pdf_url": f"/files/local-{safe_name}",
        "status": "pending",
        "uploaded_by": uploaded_by,
        "created_at": datetime.utcnow(),
        "case_number": f"LOCAL-{case_id[:8].upper()}",
    }
    cases[case_id] = case
    _save()
    return serialize_case(case)


def build_fallback_extraction(case_id: str, raw_text: str = "") -> dict:
    case = cases.get(case_id, {})
    today = datetime.utcnow().date()
    deadline = today + timedelta(days=30)
    parties = "Parties pending extraction"
    if raw_text:
        first_line = next((line.strip() for line in raw_text.splitlines() if line.strip()), "")
        if first_line:
            parties = first_line[:140]

    extraction = {
        "case_id": case_id,
        "case_number": case.get("case_number", f"LOCAL-{case_id[:8].upper()}"),
        "parties": parties,
        "date_of_order": today.isoformat(),
        "key_directions": "Uploaded locally. Full AI extraction is pending until the external AI and database services are available.",
        "compliance_deadline": deadline.isoformat(),
        "appeal_window": "Not extracted",
        "responsible_dept": "Pending review",
        "action_plan": {
            "recommendation": "review",
            "urgency": "medium",
            "required_action": "Review the uploaded judgment and complete verification.",
        },
        "source_references": {
            "compliance_deadline": "Local fallback extraction.",
            "responsible_department": "Local fallback extraction.",
        },
        "confidence_score": 0.0,
        "created_at": datetime.utcnow(),
    }
    extractions[case_id] = extraction
    if case_id in cases:
        cases[case_id].update({
            "case_number": extraction["case_number"],
            "status": "pending",
        })
    _save()
    return extraction


def create_questions(case_id: str, extraction: dict) -> list[dict]:
    prompts = [
        "What is the final order — compliance or dismissed?",
        "Which department or authority must act?",
        "What is the compliance deadline mentioned in the judgment?",
        "Is there a limitation period for appeal? If yes, what is it?",
        "What is the key directive of the court in one line?",
    ]
    ai_answers = [
        extraction.get("action_plan", {}).get("recommendation", ""),
        extraction.get("responsible_dept", ""),
        extraction.get("compliance_deadline", ""),
        extraction.get("appeal_window", ""),
        extraction.get("key_directions", ""),
    ]
    stored = []
    now = datetime.utcnow()
    for i, (prompt, answer) in enumerate(zip(prompts, ai_answers), start=1):
        stored.append({
            "id": f"{case_id}-q{i}",
            "case_id": case_id,
            "question_order": i,
            "question_text": prompt,
            "correct_answer": answer,
            "created_at": now,
        })
    questions[case_id] = stored
    _save()
    return public_questions(case_id)


def public_questions(case_id: str) -> list[dict]:
    return [
        {
            "id": q["id"],
            "question_order": q["question_order"],
            "question_text": q["question_text"],
        }
        for q in questions.get(case_id, [])
    ]


def save_submission(case_id: str, student_id: str, answers: dict, scoring_result: dict) -> dict:
    key = f"{case_id}:{student_id}"
    submission = {
        "id": key,
        "case_id": case_id,
        "student_id": student_id,
        "answers": answers,
        "match_score": scoring_result["match_score"],
        "status": scoring_result["status"],
        "breakdown": scoring_result["breakdown"],
        "submitted_at": datetime.utcnow(),
    }
    submissions[key] = submission
    if case_id in cases:
        cases[case_id]["status"] = "flagged"
    _save()
    return submission


def submission_for(case_id: str, student_id: str) -> dict | None:
    return submissions.get(f"{case_id}:{student_id}")


def latest_submission(case_id: str) -> dict | None:
    matches = [s for s in submissions.values() if s.get("case_id") == case_id]
    if not matches:
        return None
    return sorted(matches, key=lambda item: str(item.get("submitted_at") or ""), reverse=True)[0]


def serialize_extraction(extraction: dict) -> dict:
    data = dict(extraction)
    created_at = data.get("created_at")
    if created_at and hasattr(created_at, "isoformat"):
        data["created_at"] = created_at.isoformat()
    return data


def serialize_submission(submission: dict) -> dict:
    data = dict(submission)
    submitted_at = data.get("submitted_at")
    if submitted_at and hasattr(submitted_at, "isoformat"):
        data["submitted_at"] = submitted_at.isoformat()
    return data
