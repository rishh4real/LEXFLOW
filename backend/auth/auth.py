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

from database.db import get_connection

load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────────
SECRET_KEY = os.getenv("JWT_SECRET", "change-me-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24

# ── Helpers ───────────────────────────────────────────────────────────────────
bearer_scheme = HTTPBearer()


def hash_password(plain: str) -> str:
    """Hash a plain-text password with bcrypt."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(plain.encode('utf-8'), salt).decode('utf-8')


def verify_password(plain: str, hashed: str) -> bool:
    """Return True if plain password matches stored hash."""
    return bcrypt.checkpw(plain.encode('utf-8'), hashed.encode('utf-8'))


def create_access_token(user_id: int, email: str, role: str) -> str:
    """
    Build a signed JWT token containing:
      sub  = user email
      id   = user id
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
def authenticate_user(email: str, password: str) -> Optional[dict]:
    """
    Look up user by email, verify password.
    Returns user row dict on success, None on failure.
    """
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM users WHERE email = ?", (email,)
    ).fetchone()
    conn.close()

    if not row:
        return None
    if not verify_password(password, row["password_hash"]):
        return None
    return dict(row)
