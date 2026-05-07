"""
database/mongo.py
-----------------
MongoDB (Atlas) initialization for LexFlow using Motor (async).

Env vars:
  - MONGODB_URI: Mongo connection string (mongodb+srv://...)
  - MONGODB_DB_NAME: database name (default: "lexflow")
"""

import os

import certifi
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase, AsyncIOMotorGridFSBucket
from dotenv import load_dotenv

load_dotenv()

MONGODB_URI_ENV_KEYS = ("MONGODB_URI", "MONGO_URI", "MONGODB_URL", "DATABASE_URL")

_client: AsyncIOMotorClient | None = None
_db: AsyncIOMotorDatabase | None = None
_fs: AsyncIOMotorGridFSBucket | None = None


def is_production_runtime() -> bool:
    return os.getenv("ENVIRONMENT") == "production" or os.getenv("RENDER") == "true"


def mongodb_uri_configured() -> bool:
    return bool(get_mongodb_uri())


def get_mongodb_uri() -> str | None:
    for key in MONGODB_URI_ENV_KEYS:
        value = os.getenv(key)
        if value and value.strip():
            return value.strip()
    return None


def get_client() -> AsyncIOMotorClient:
    global _client
    if _client is None:
        uri = get_mongodb_uri()
        if not uri:
            keys = ", ".join(MONGODB_URI_ENV_KEYS)
            raise RuntimeError(f"MongoDB URI is not set. Expected one of: {keys}")
        _client = AsyncIOMotorClient(
            uri,
            serverSelectionTimeoutMS=5000,
            tlsCAFile=certifi.where(),
        )
    return _client


def get_db() -> AsyncIOMotorDatabase:
    global _db
    if _db is None:
        name = os.getenv("MONGODB_DB_NAME", "lexflow")
        _db = get_client()[name]
    return _db


def get_fs() -> AsyncIOMotorGridFSBucket:
    global _fs
    if _fs is None:
        _fs = AsyncIOMotorGridFSBucket(get_db())
    return _fs


async def ensure_indexes() -> None:
    """
    Create minimal indexes for hackathon scale.
    Safe to call multiple times.
    """
    db = get_db()
    await db.users.create_index("email", unique=True)
    await db.cases.create_index([("status", 1), ("created_at", -1)])
    await db.extractions.create_index("case_id", unique=True)
    await db.quiz_questions.create_index([("case_id", 1), ("question_order", 1)])
    await db.quiz_submissions.create_index([("case_id", 1), ("student_id", 1)], unique=True)
    await db.verifications.create_index([("case_id", 1), ("created_at", -1)])
