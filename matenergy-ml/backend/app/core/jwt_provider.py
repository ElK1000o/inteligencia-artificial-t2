"""
JWT token creation and validation using PyJWT (never python-jose).

Tokens are signed with HMAC-SHA256.  Every token carries the standard claims
iss, aud, sub, iat, nbf, exp plus jti (unique token id) and a custom 'type'
claim (access | refresh) to prevent token-type confusion attacks.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt

from app.core.config import settings
from app.core.constants import TokenType
from app.core.exceptions import (
    TokenExpiredError,
    TokenInvalidError,
    TokenTypeMismatchError,
)

ALGORITHM = "HS256"

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _utcnow() -> datetime:
    """Return the current UTC time as a timezone-aware datetime."""
    return datetime.now(tz=timezone.utc)


def _build_base_payload(subject: str, token_type: TokenType, expire: datetime) -> dict[str, Any]:
    now = _utcnow()
    return {
        "iss": settings.JWT_ISSUER,
        "aud": settings.JWT_AUDIENCE,
        "sub": subject,
        "iat": now,
        "nbf": now,
        "exp": expire,
        "jti": str(uuid.uuid4()),
        "type": token_type.value,
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def create_access_token(
    subject: str,
    additional_claims: dict[str, Any] | None = None,
) -> str:
    """
    Create a short-lived JWT access token.

    Args:
        subject: Unique identifier for the token owner (e.g. user UUID as str).
        additional_claims: Optional dict merged into the payload *after* standard
            claims are set.  Standard claims (sub, exp, …) cannot be overridden.

    Returns:
        Signed JWT string.
    """
    expire = _utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = _build_base_payload(subject, TokenType.ACCESS, expire)
    if additional_claims:
        # Merge additional claims but protect reserved standard claims from override
        reserved = {"iss", "aud", "sub", "iat", "nbf", "exp", "jti", "type"}
        safe_extra = {k: v for k, v in additional_claims.items() if k not in reserved}
        payload.update(safe_extra)
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(subject: str) -> tuple[str, str]:
    """
    Create a long-lived JWT refresh token.

    Args:
        subject: Unique identifier for the token owner.

    Returns:
        Tuple of (signed JWT string, jti UUID string).
        The jti should be persisted so it can be revoked on logout.
    """
    expire = _utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    payload = _build_base_payload(subject, TokenType.REFRESH, expire)
    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=ALGORITHM)
    return token, payload["jti"]


def decode_token(token: str, expected_type: TokenType) -> dict[str, Any]:
    """
    Decode and fully validate a JWT token.

    Validation steps performed by PyJWT:
      - Signature verification (HS256 + JWT_SECRET_KEY)
      - exp / nbf / iat time-window checks
      - iss / aud claim matching
      - Presence of all required claims

    Additional validation performed here:
      - Token type must match *expected_type*

    Args:
        token: Raw JWT string from the Authorization header.
        expected_type: The TokenType this token must be (ACCESS or REFRESH).

    Returns:
        Decoded payload dict.

    Raises:
        TokenExpiredError: Token exp is in the past.
        TokenTypeMismatchError: Token type claim does not match expected_type.
        TokenInvalidError: Any other JWT validation failure.
    """
    try:
        payload: dict[str, Any] = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[ALGORITHM],
            issuer=settings.JWT_ISSUER,
            audience=settings.JWT_AUDIENCE,
            options={
                "require": ["exp", "iat", "nbf", "sub", "jti", "type", "iss", "aud"],
                "verify_exp": True,
                "verify_nbf": True,
                "verify_iat": True,
                "verify_iss": True,
                "verify_aud": True,
                "verify_signature": True,
            },
        )
    except jwt.ExpiredSignatureError:
        raise TokenExpiredError(
            code="TOKEN_EXPIRED",
            message="Token expired",
            detail="JWT exp claim is in the past",
            recommended_action="Request a new token via /auth/refresh or log in again",
        )
    except jwt.InvalidTokenError as exc:
        raise TokenInvalidError(
            code="TOKEN_INVALID",
            message="Invalid token",
            detail=f"JWT validation failed: {type(exc).__name__}: {exc}",
            recommended_action="Provide a valid, properly signed token",
        )

    # Type-confusion guard: verify the custom 'type' claim explicitly
    token_type_value = payload.get("type")
    if token_type_value != expected_type.value:
        raise TokenTypeMismatchError(
            code="TOKEN_TYPE_MISMATCH",
            message="Invalid token type",
            detail=(
                f"Expected token type '{expected_type.value}', "
                f"got '{token_type_value}'"
            ),
            recommended_action=(
                "Use an access token for API calls and a refresh token for /auth/refresh"
            ),
        )

    return payload


def validate_token_claims(payload: dict[str, Any]) -> None:
    """
    Additional application-level claim validation beyond PyJWT defaults.

    This is a secondary defence useful when payloads are reconstructed from
    storage rather than decoded fresh from a signed JWT.

    Raises:
        TokenInvalidError: If any required claim is missing.
    """
    required: set[str] = {"sub", "jti", "type", "iss", "aud"}
    missing = required - payload.keys()
    if missing:
        raise TokenInvalidError(
            code="TOKEN_MISSING_CLAIMS",
            message="Invalid token",
            detail=f"Missing required claims: {sorted(missing)}",
            recommended_action="Provide a complete, unmodified token",
        )

    # sub must be a non-empty string
    sub = payload.get("sub", "")
    if not isinstance(sub, str) or not sub.strip():
        raise TokenInvalidError(
            code="TOKEN_INVALID_SUB",
            message="Invalid token",
            detail="'sub' claim is empty or not a string",
            recommended_action="Provide a valid token issued by this service",
        )
