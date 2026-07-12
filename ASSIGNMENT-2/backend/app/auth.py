"""Authentication module — password hashing, session tokens, and FastAPI dependency.

Uses PBKDF2-HMAC-SHA256 (from the standard library ``hashlib``) for password
hashing and ``secrets.token_urlsafe`` for session tokens. No external
dependencies required.
"""

from __future__ import annotations

import hashlib
import secrets

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .db import create_session, create_user, delete_session, get_session, get_user_by_email

# Bearer token security scheme
_security = HTTPBearer(auto_error=False)


def _hash_password(password: str, salt: str) -> str:
    """Hash a password with a salt using PBKDF2-HMAC-SHA256."""
    return hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        iterations=100_000,
    ).hex()


def _generate_salt() -> str:
    """Generate a random salt."""
    return secrets.token_hex(16)


def register_user(email: str, password: str) -> dict:
    """Register a new user.

    Returns:
        A dict with ``token`` and ``email`` on success.

    Raises:
        ValueError: If the email is already registered.
    """
    if not email or "@" not in email:
        raise ValueError("A valid email address is required.")
    if not password or len(password) < 6:
        raise ValueError("Password must be at least 6 characters long.")

    salt = _generate_salt()
    password_hash = _hash_password(password, salt)

    if not create_user(email, password_hash, salt):
        raise ValueError("An account with this email already exists.")

    # Create a session
    user = get_user_by_email(email)
    token = create_session(user["id"], email)

    return {"token": token, "email": email}


def login_user(email: str, password: str) -> dict:
    """Authenticate a user and return a session token.

    Returns:
        A dict with ``token`` and ``email`` on success.

    Raises:
        ValueError: If credentials are invalid.
    """
    user = get_user_by_email(email)
    if user is None:
        raise ValueError("Invalid email or password.")

    password_hash = _hash_password(password, user["salt"])
    if not secrets.compare_digest(password_hash, user["password_hash"]):
        raise ValueError("Invalid email or password.")

    token = create_session(user["id"], email)
    return {"token": token, "email": email}


def logout_user(token: str) -> None:
    """Delete a session (logout)."""
    delete_session(token)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_security),
) -> dict:
    """FastAPI dependency that extracts and validates the Bearer token.

    Returns:
        A dict with ``email`` and ``token`` of the authenticated user.

    Raises:
        HTTPException: 401 if the token is missing or invalid.
    """
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please login.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    session = get_session(token)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session. Please login again.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return {"email": session["email"], "token": token}
