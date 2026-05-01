"""
database/db.py
--------------
SQLite connection management and table initialisation for LexFlow.
On startup, creates all tables if they do not already exist.
"""

import sqlite3
import os
from pathlib import Path

# Resolve DB path from env or default to project root
DB_PATH = os.getenv("DATABASE_URL", "sqlite:///./lexflow.db").replace("sqlite:///", "")


def get_connection() -> sqlite3.Connection:
    """Return a new SQLite connection with row_factory for dict-like rows."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row  # rows behave like dicts
    conn.execute("PRAGMA journal_mode=WAL")  # better concurrency
    return conn


def init_db():
    """
    Create all tables on first run.
    Called once when FastAPI starts up.
    """
    conn = get_connection()
    cursor = conn.cursor()

    # ── users ─────────────────────────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            name          TEXT    NOT NULL,
            email         TEXT    NOT NULL UNIQUE,
            password_hash TEXT    NOT NULL,
            role          TEXT    NOT NULL DEFAULT 'student',  -- admin | student | official
            invite_code   TEXT,
            created_at    DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # ── cases ─────────────────────────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cases (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            case_number TEXT,
            pdf_path    TEXT    NOT NULL,
            raw_text    TEXT,
            status      TEXT    NOT NULL DEFAULT 'pending',  -- pending | verified | flagged
            uploaded_by INTEGER REFERENCES users(id),
            created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # ── extractions ───────────────────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS extractions (
            id                   INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id              INTEGER NOT NULL REFERENCES cases(id),
            case_number          TEXT,
            parties              TEXT,
            date_of_order        TEXT,
            key_directions       TEXT,
            compliance_deadline  TEXT,
            appeal_window        TEXT,
            responsible_dept     TEXT,
            action_plan          TEXT,   -- JSON string
            source_references    TEXT,   -- JSON string: field_name → exact sentence
            confidence_score     REAL,
            created_at           DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # ── quiz_questions ────────────────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS quiz_questions (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id       INTEGER NOT NULL REFERENCES cases(id),
            question_text TEXT    NOT NULL,
            correct_answer TEXT   NOT NULL,  -- stored server-side, never sent before submission
            question_order INTEGER,
            created_at    DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # ── quiz_submissions ──────────────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS quiz_submissions (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id      INTEGER NOT NULL REFERENCES cases(id),
            student_id   INTEGER NOT NULL REFERENCES users(id),
            answers_json TEXT    NOT NULL,  -- JSON: {question_id: student_answer}
            match_score  REAL,             -- 0.0 – 100.0
            status       TEXT    DEFAULT 'pending',  -- pending | approved | flagged
            submitted_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # ── verifications ─────────────────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS verifications (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id     INTEGER NOT NULL REFERENCES cases(id),
            status      TEXT    NOT NULL,  -- approved | flagged | rejected
            reviewed_by INTEGER REFERENCES users(id),
            notes       TEXT,
            verified_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()
    print("✅  Database initialised at:", DB_PATH)
