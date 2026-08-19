"""Authentication and Token Management Endpoints."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from backend.config import config
from backend.security.auth import (
    ClientCredentialsRequest,
    TokenPayload,
    TokenResponse,
    create_access_token,
    get_current_auth,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


class TokenRequest(BaseModel):
    """Token request payload using API key or client credentials."""

    api_key: str
    org_id: str = "default"
    client_name: str = "grantscout-client"


@router.post("/token", response_model=TokenResponse)
async def generate_access_token(payload: TokenRequest):
    """Exchange a valid API Key for a scoped Bearer JWT access token."""
    if payload.api_key != config.MASTER_API_KEY:
        logger.warning(f"Failed token generation attempt for client: {payload.client_name}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key provided.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    expires_delta = timedelta(minutes=config.ACCESS_TOKEN_EXPIRE_MINUTES)
    token_claims = {
        "sub": payload.client_name,
        "org_id": payload.org_id,
        "role": "admin",
        "scopes": ["read", "write", "agent:execute"],
    }

    access_token = create_access_token(token_claims, expires_delta=expires_delta)
    now_str = datetime.now(timezone.utc).isoformat()

    logger.info(f"Issued access token for client: {payload.client_name} (org: {payload.org_id})")

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in_seconds=config.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        issued_at=now_str,
    )


@router.get("/verify")
async def verify_token_endpoint(auth_payload: TokenPayload = Depends(get_current_auth)):
    """Verify that the provided Bearer token or API key is valid."""
    return {
        "status": "valid",
        "authenticated": True,
        "identity": {
            "subject": auth_payload.sub,
            "org_id": auth_payload.org_id,
            "role": auth_payload.role,
            "scopes": auth_payload.scopes,
        },
    }


@router.get("/me")
async def get_current_user_profile(auth_payload: TokenPayload = Depends(get_current_auth)):
    """Get the authenticated subject claims and active permissions."""
    return {
        "user_id": auth_payload.sub,
        "org_id": auth_payload.org_id,
        "role": auth_payload.role,
        "permissions": auth_payload.scopes,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
