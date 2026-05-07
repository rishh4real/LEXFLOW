"""
auth/auth.py
------------
JWT authentication for LexFlow.
- Creates access tokens with role + user_id embedded
- Provides FastAPI dependency `get_current_user` used in route guards
- Passwords hashed with bcrypt
"""

import os
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
import bcrypt
from dotenv import load_dotenv

from bson import ObjectId
from database.mongo import get_db, is_production_runtime

load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────────
SECRET_KEY = os.getenv("JWT_SECRET", "change-me-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24

DEMO_USERS = {
    "admin@lexflow.com": {
        "id": "000000000000000000000001",
        "name": "Admin User",
        "email": "admin@lexflow.com",
        "password": "admin123",
        "role": "admin",
    },
    "student@lexflow.com": {
        "id": "000000000000000000000002",
        "name": "Law Student",
        "email": "student@lexflow.com",
        "password": "student123",
        "role": "student",
    },
    "official@lexflow.com": {
        "id": "000000000000000000000003",
        "name": "Govt Official",
        "email": "official@lexflow.com",
        "password": "official123",
        "role": "official",
    },
}

# ── Helpers ───────────────────────────────────────────────────────────────────
bearer_scheme = HTTPBearer()


def hash_password(plain: str) -> str:
    """Hash a plain-text password with bcrypt."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(plain.encode('utf-8'), salt).decode('utf-8')


def verify_password(plain: str, hashed: str) -> bool:
    """Return True if plain password matches stored hash."""
    return bcrypt.checkpw(plain.encode('utf-8'), hashed.encode('utf-8'))


def create_access_token(user_id: str, email: str, role: str) -> str:
    """
    Build a signed JWT token containing:
      sub  = user email
      id   = user id (string)
      role = user role (admin | student | official)
      exp  = expiry timestamp
    """
    expire = datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    payload = {
        "sub": email,
        "id": user_id,
        "role": role,
        "exp": expire,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    """Decode JWT and return payload dict. Raises HTTPException on failure."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ── FastAPI dependency ─────────────────────────────────────────────────────────
def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> dict:
    """
    FastAPI dependency — inject into any route to require authentication.
    Returns decoded token payload: { sub, id, role }.
    """
    return decode_token(credentials.credentials)


# ── Login helper ───────────────────────────────────────────────────────────────
async def authenticate_user(email: str, password: str) -> Optional[dict]:
    """
    Look up user by email in MongoDB, verify password.
    Returns user data on success, None on failure.
    """
    try:
        db = get_db()
        user_doc = await db.users.find_one({"email": email})
    except Exception:
        if is_production_runtime():
            return None
        demo = DEMO_USERS.get(email)
        if demo and demo["password"] == password:
            return {key: value for key, value in demo.items() if key != "password"}
        return None

    if not user_doc:
        return None

    user_data = dict(user_doc)
    user_data["id"] = str(user_data.pop("_id"))

    if not verify_password(password, user_data["password_hash"]):
        return None
    
    return user_data
