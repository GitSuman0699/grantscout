"""GrantScout Security & Authentication Layer.

Provides:
- JWT Access Token issuance and verification
- Master & Scoped API Key authentication
- FastAPI Security Dependency (`get_current_auth`)
- Input Sanitization & Prompt Injection defense for Agent tools
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import jwt
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.security.api_key import APIKeyHeader
from pydantic import BaseModel

from backend.config import config

logger = logging.getLogger(__name__)

# Security schemes
bearer_scheme = HTTPBearer(auto_error=False)
api_key_header_scheme = APIKeyHeader(name="X-API-Key", auto_error=False)


# ──────────────────────────────────────────────
#  Token Schemas
# ──────────────────────────────────────────────


class TokenPayload(BaseModel):
    """Decoded JWT claims payload."""

    sub: str
    org_id: str = "default"
    role: str = "admin"
    scopes: list[str] = ["read", "write", "agent:execute"]
    exp: Optional[int] = None
    iat: Optional[int] = None


class TokenResponse(BaseModel):
    """Token generation response."""

    access_token: str
    token_type: str = "bearer"
    expires_in_seconds: int
    issued_at: str


class ClientCredentialsRequest(BaseModel):
    """Client credentials request for access token issuance."""

    client_id: str
    client_secret: str
    org_id: str = "default"


# ──────────────────────────────────────────────
#  JWT Utilities
# ──────────────────────────────────────────────


def create_access_token(
    data: dict[str, Any],
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Generate a signed JWT access token.

    Args:
        data: Claims dictionary to encode.
        expires_delta: Optional custom expiration window.

    Returns:
        Encoded JWT token string.
    """
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=config.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({
        "exp": int(expire.timestamp()),
        "iat": int(now.timestamp()),
    })

    encoded_jwt = jwt.encode(
        to_encode,
        config.SECRET_KEY,
        algorithm=config.ALGORITHM,
    )
    return encoded_jwt


def verify_access_token(token: str) -> TokenPayload:
    """Verify and decode a JWT token string.

    Args:
        token: Bearer JWT string.

    Raises:
        HTTPException: If token is expired, invalid, or malformed.

    Returns:
        Validated TokenPayload instance.
    """
    try:
        payload = jwt.decode(
            token,
            config.SECRET_KEY,
            algorithms=[config.ALGORITHM],
        )
        sub = payload.get("sub")
        if not sub:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token validation failed: missing subject claim",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return TokenPayload(**payload)

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access token has expired. Please refresh or authenticate again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid authentication token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ──────────────────────────────────────────────
#  FastAPI Authentication Dependency
# ──────────────────────────────────────────────


async def get_current_auth(
    bearer_auth: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme),
    api_key_header: Optional[str] = Security(api_key_header_scheme),
) -> TokenPayload:
    """Validate incoming request authorization via JWT Bearer or API Key.

    Validation Order:
    1. If AUTH_ENABLED is False, returns default authenticated admin context.
    2. Check `X-API-Key` header against MASTER_API_KEY.
    3. Check `Authorization: Bearer <key>` against MASTER_API_KEY.
    4. Check `Authorization: Bearer <jwt>` as a signed JWT token.

    Returns:
        TokenPayload containing authenticated identity and scopes.
    """
    # Bypass when auth is explicitly disabled
    if not config.AUTH_ENABLED:
        return TokenPayload(sub="dev_user", org_id="default", role="admin")

    # 1. Check X-API-Key header
    if api_key_header:
        if api_key_header == config.MASTER_API_KEY:
            return TokenPayload(
                sub="api_key_client",
                org_id="default",
                role="system",
                scopes=["read", "write", "agent:execute"],
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API Key provided in X-API-Key header.",
                headers={"WWW-Authenticate": "ApiKey"},
            )

    # 2. Check Authorization Bearer header
    if bearer_auth and bearer_auth.credentials:
        token_str = bearer_auth.credentials.strip()

        # Check if the bearer token is the master API key
        if token_str == config.MASTER_API_KEY:
            return TokenPayload(
                sub="api_key_client",
                org_id="default",
                role="system",
                scopes=["read", "write", "agent:execute"],
            )

        # Decode as standard JWT token
        return verify_access_token(token_str)

    # If neither provided
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required. Provide a Bearer JWT token or X-API-Key header.",
        headers={"WWW-Authenticate": "Bearer"},
    )


# ──────────────────────────────────────────────
#  Input Sanitization & Injection Defense
# ──────────────────────────────────────────────


SUSPICIOUS_PATTERNS = [
    r"(?i)ignore\s+(all\s+)?(previous|prior)\s+instructions",
    r"(?i)system\s+prompt\s+override",
    r"(?i)disregard\s+the\s+above",
    r"(?i)you\s+are\s+now\s+in\s+dan\s+mode",
    r"(?i)jailbreak",
]


def sanitize_input(text: str, field_name: str = "input") -> str:
    """Sanitize user input against prompt injection patterns and malicious tags.

    Args:
        text: Raw user-provided text.
        field_name: Contextual field name for logging.

    Returns:
        Sanitized text string.
    """
    if not text:
        return ""

    # Strip dangerous control characters
    cleaned = "".join(ch for ch in text if ch.isprintable() or ch in "\n\r\t")

    # Detect known injection signatures
    for pattern in SUSPICIOUS_PATTERNS:
        if re.search(pattern, cleaned):
            logger.warning(f"Potential injection attempt detected in {field_name}: {pattern}")
            # Neutralize command trigger by wrapping in safe quote notation
            cleaned = re.sub(pattern, "[FILTERED_INSTRUCTION]", cleaned)

    return cleaned.strip()
