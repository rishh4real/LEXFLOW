"""
auth/roles.py
-------------
Role-based access control (RBAC) for LexFlow.
Three roles: admin, student, official.
Use as FastAPI dependencies in route decorators.
"""

from fastapi import Depends, HTTPException, status
from auth.auth import get_current_user


def _require_role(*allowed_roles: str):
    """
    Factory that returns a FastAPI dependency checking for specific roles.
    Usage: Depends(require_admin)  or  Depends(require_roles("admin", "official"))
    """
    def dependency(current_user: dict = Depends(get_current_user)) -> dict:
        if current_user.get("role") not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role(s): {', '.join(allowed_roles)}",
            )
        return current_user
    return dependency


# ── Role dependencies — import these in route files ───────────────────────────

def require_admin(current_user: dict = Depends(get_current_user)) -> dict:
    """Only admin users can access this route."""
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required.",
        )
    return current_user


def require_student(current_user: dict = Depends(get_current_user)) -> dict:
    """Only student users can access this route."""
    if current_user.get("role") != "student":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Student access required.",
        )
    return current_user


def require_official(current_user: dict = Depends(get_current_user)) -> dict:
    """Only official (government) users can access this route."""
    if current_user.get("role") != "official":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Official access required.",
        )
    return current_user


def require_admin_or_official(current_user: dict = Depends(get_current_user)) -> dict:
    """Admins and officials can both access this route."""
    if current_user.get("role") not in ("admin", "official"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin or Official access required.",
        )
    return current_user
