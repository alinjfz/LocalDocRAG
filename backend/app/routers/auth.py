"""
DocMind auth router.

Endpoints:
  POST /api/auth/login   — returns JWT access token

Also exports get_current_user dependency used by all protected endpoints.
"""

import logging
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import settings
from app.models import LoginRequest, TokenResponse
from app.services.auth import authenticate_user, create_access_token, verify_token

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/auth", tags=["auth"])

_bearer_scheme = HTTPBearer(auto_error=True)


# Validate Bearer token and return username
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
) -> str:
    payload = verify_token(credentials.credentials)
    username: str = payload.get("sub", "")
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token payload missing 'sub' claim.",
        )
    return username


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Authenticate and receive a JWT access token",
)
# Validate credentials and return a JWT token
async def login(request: LoginRequest) -> TokenResponse:
    if not authenticate_user(request.username, request.password):
        logger.warning("Failed login attempt for username='%s'", request.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password.",
        )

    token = create_access_token(
        data={"sub": request.username},
        expires_delta=timedelta(minutes=settings.JWT_EXPIRE_MINUTES),
    )
    logger.info("Successful login: username='%s'", request.username)

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=settings.JWT_EXPIRE_MINUTES * 60,
    )
