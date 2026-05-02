"""
DocMind authentication service.

Handles password verification (bcrypt) and JWT token creation/validation.
Single-user model: credentials are stored in environment variables, not a DB.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from fastapi import HTTPException, status
from jose import JWTError, jwt

from app.config import settings

logger = logging.getLogger(__name__)


# Check plaintext password against bcrypt hash
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8"),
    )


# Hash a plaintext password with bcrypt
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


# Validate username and password against settings
def authenticate_user(username: str, password: str) -> bool:
    if username != settings.APP_USERNAME:
        return False
    if not settings.APP_PASSWORD_HASH:
        logger.error("APP_PASSWORD_HASH is not set — cannot authenticate")
        return False
    return verify_password(password, settings.APP_PASSWORD_HASH)


# Sign and return a JWT with expiry
def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None,
) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    )
    to_encode["exp"] = expire
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


# Decode JWT, raise 401 if invalid or expired
def verify_token(token: str) -> dict:
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        return payload
    except JWTError as exc:
        logger.warning("JWT validation failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
