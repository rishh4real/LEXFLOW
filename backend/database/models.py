"""
database/models.py
------------------
Dataclass-style Python models (typed dicts) for LexFlow tables.
Used for type hints and serialisation throughout the app.
These are NOT ORM models — we use raw sqlite3 for simplicity.
"""

from typing import Optional, List
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class User:
    id: Optional[int]
    name: str
    email: str
    password_hash: str
    role: str = "student"          # admin | student | official
    invite_code: Optional[str] = None
    created_at: Optional[str] = None


@dataclass
class Case:
    id: Optional[int]
    case_number: Optional[str]
    pdf_path: str
    raw_text: Optional[str]
    status: str = "pending"        # pending | verified | flagged
    uploaded_by: Optional[int] = None
    created_at: Optional[str] = None


@dataclass
class Extraction:
    id: Optional[int]
    case_id: int
    case_number: Optional[str]
    parties: Optional[str]
    date_of_order: Optional[str]
    key_directions: Optional[str]
    compliance_deadline: Optional[str]
    appeal_window: Optional[str]
    responsible_dept: Optional[str]
    action_plan: Optional[str]       # JSON string
    source_references: Optional[str] # JSON string
    confidence_score: Optional[float]
    created_at: Optional[str] = None


@dataclass
class QuizQuestion:
    id: Optional[int]
    case_id: int
    question_text: str
    correct_answer: str              # NEVER returned to frontend pre-submission
    question_order: Optional[int]
    created_at: Optional[str] = None


@dataclass
class QuizSubmission:
    id: Optional[int]
    case_id: int
    student_id: int
    answers_json: str               # JSON string
    match_score: Optional[float]
    status: str = "pending"         # pending | approved | flagged
    submitted_at: Optional[str] = None


@dataclass
class Verification:
    id: Optional[int]
    case_id: int
    status: str                     # approved | flagged | rejected
    reviewed_by: Optional[int]
    notes: Optional[str]
    verified_at: Optional[str] = None
