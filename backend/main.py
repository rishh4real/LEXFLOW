"""
main.py
-------
LexFlow FastAPI application entry point.
- Mounts all routers
- Configures CORS for React frontend (localhost:5173)
- Initialises SQLite database on startup
- Provides /auth/login and /auth/register endpoints
- Swagger UI available at /docs
"""

import os
import secrets
from datetime import datetime
from typing import Optional, List
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from database.mongo import get_db, ensure_indexes
from auth.auth import (
    authenticate_user,
    create_access_token,
    hash_password,
    get_current_user,
)
from auth.roles import require_admin
from routes import cases, extraction, quiz, verification, dashboard, files

# ── App factory ───────────────────────────────────────────────────────────────
app = FastAPI(
    title="LexFlow API",
    description="AI-Powered Court Judgment Intelligence System",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    root_path="/api" if os.getenv("ENVIRONMENT") == "production" else "",
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Mount routers ─────────────────────────────────────────────────────────────
app.include_router(cases.router)
app.include_router(extraction.router)
app.include_router(quiz.router)
app.include_router(verification.router)
app.include_router(dashboard.router)
app.include_router(files.router)


# ── Startup: initialise Mongo + seed demo users ───────────────────────────────
@app.on_event("startup")
async def on_startup():
    try:
        await ensure_indexes()
        await _seed_demo_users()
    except Exception as exc:
        print(f"⚠️  MongoDB unavailable; demo login fallback is active. ({exc})")


async def _seed_demo_users():
    """
    Create demo users in MongoDB if collection is empty.
    Demo credentials:
      admin@lexflow.com   / admin123   → role: admin
      student@lexflow.com / student123 → role: student
      official@lexflow.com/ official123→ role: official
    """
    db = get_db()
    count = await db.users.count_documents({})

    if count == 0:
        demos = [
            ("Admin User",    "admin@lexflow.com",    "admin123",    "admin"),
            ("Law Student",   "student@lexflow.com",  "student123",  "student"),
            ("Govt Official", "official@lexflow.com", "official123", "official"),
        ]
        for name, email, pwd, role in demos:
            await db.users.insert_one({
                "name": name,
                "email": email,
                "password_hash": hash_password(pwd),
                "role": role,
                "created_at": datetime.utcnow()
            })
        print("✅  Demo users seeded in MongoDB (admin / student / official)")


# ── Auth endpoints ────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: str
    password: str


class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str
    role: str = "student"         # default role
    invite_code: str | None = None


@app.post("/auth/login", tags=["Auth"])
async def login(body: LoginRequest):
    """
    Authenticate user with email + password.
    Returns JWT token + user info (role determines frontend redirect).
    """
    user = await authenticate_user(body.email, body.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )
    token = create_access_token(user["id"], user["email"], user["role"])
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "role": user["role"],
        },
    }


@app.post("/auth/register", tags=["Auth"])
async def register(body: RegisterRequest):
    """
    Register a new user in MongoDB.
    """
    db = get_db()

    # Check email uniqueness
    existing = await db.users.find_one({"email": body.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered.")

    # Validate invite code for student role
    if body.role == "student" and body.invite_code:
        valid = await db.users.find_one({"invite_code": body.invite_code})
        if not valid:
            raise HTTPException(status_code=403, detail="Invalid invite code.")

    try:
        await db.users.insert_one({
            "name": body.name,
            "email": body.email,
            "password_hash": hash_password(body.password),
            "role": body.role,
            "created_at": datetime.utcnow()
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")

    return {"message": "Account created successfully. Please log in."}


@app.post("/auth/invite", tags=["Auth"])
async def generate_invite(current_user: dict = Depends(require_admin)):
    """Admin generates a one-time invite code for a student in MongoDB."""
    code = secrets.token_urlsafe(12)
    db = get_db()
    try:
        from bson import ObjectId
        await db.users.update_one({"_id": ObjectId(current_user["id"])}, {"$set": {"invite_code": code}})
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to generate invite.")
        
    return {"invite_code": code}


@app.get("/auth/me", tags=["Auth"])
def me(current_user: dict = Depends(get_current_user)):
    """Return current user info from JWT."""
    return current_user


from services.llm_service import extract_case, client as groq_client

# ... existing code ...

# ── AI Chatbot ────────────────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    message: str
    context: Optional[str] = None  # Optional case context

@app.post("/chat", tags=["AI Assistance"])
def chat_assistant(body: ChatRequest, current_user: dict = Depends(get_current_user)):
    """
    AI Chatbot to help users understand judgments or navigate the platform.
    """
    try:
        system_prompt = (
            "You are LexFlow Assistant, an AI expert in Indian legal judgments. "
            "Help the user understand court orders, legal terms, and administrative procedures. "
            "Keep responses concise, professional, and helpful. "
            f"User role: {current_user['role']}"
        )
        
        messages = [
            {"role": "system", "content": system_prompt},
        ]
        
        if body.context:
            messages.append({"role": "system", "content": f"Context: {body.context}"})
            
        messages.append({"role": "user", "content": body.message})

        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            temperature=0.7,
            max_tokens=500,
        )
        
        return {"response": response.choices[0].message.content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")


# ── Health check ──────────────────────────────────────────────────────────────
@app.get("/health", tags=["System"])
def health():
    return {"status": "ok", "service": "LexFlow API"}


@app.get("/health/db", tags=["System"])
async def health_db():
    try:
        await get_db().command("ping")
        return {"status": "ok", "database": "connected"}
    except Exception as exc:
        return JSONResponse(
            status_code=503,
            content={"status": "error", "database": "unavailable", "detail": str(exc)[:500]},
        )

# ── User Management ───────────────────────────────────────────────────────────
@app.get("/admin/users", tags=["Admin"])
async def list_users(current_user: dict = Depends(require_admin)):
    """
    List all users in the system for admin review.
    """
    db = get_db()

    users = []
    async for doc in db.users.find({}):
        data = dict(doc)
        users.append({
            "id": str(data.get("_id")),
            "name": data.get("name"),
            "email": data.get("email"),
            "role": data.get("role"),
            "created_at": data.get("created_at").isoformat() if data.get("created_at") else None
        })
    return users
