"""Password hashing (Argon2) and session tokens (JWT in an httpOnly cookie)."""

from datetime import UTC, datetime, timedelta

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError
from fastapi import Response

from betteru.config import get_settings

COOKIE_NAME = "betteru_session"
_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, InvalidHashError):
        return False


def create_token(user_id: int, days: int | None = None) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    payload = {"sub": str(user_id), "iat": now, "exp": now + timedelta(days=days or settings.jwt_expiry_days)}
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def decode_token(token: str) -> int | None:
    try:
        payload = jwt.decode(token, get_settings().jwt_secret, algorithms=["HS256"])
        return int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        return None


def set_session_cookie(response: Response, user_id: int, days: int | None = None) -> None:
    settings = get_settings()
    days = days or settings.jwt_expiry_days
    response.set_cookie(
        COOKIE_NAME,
        create_token(user_id, days),
        max_age=days * 86400,
        httponly=True,  # not readable from JavaScript, so XSS can't steal it
        samesite="lax",  # blocks cross-site POSTs (CSRF)
        secure=settings.cookie_secure,
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(COOKIE_NAME, path="/")
