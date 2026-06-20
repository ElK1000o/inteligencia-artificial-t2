"""
FastAPI security dependencies for MatEnergy-ML.

Provides reusable ``Depends``-compatible callables for:
  - Extracting and validating the Bearer token (``get_current_user_payload``)
  - Role-based access control (``require_roles``)
  - Fine-grained permission checks (``require_permission_dep``)

All authentication errors are surfaced as HTTP 401/403 with a
``WWW-Authenticate: Bearer`` header so clients can react correctly.

Example usage in a router:
    from app.core.security import get_current_user_payload, require_roles, require_permission_dep
    from app.core.constants import UserRole

    # Any authenticated user
    @router.get("/me")
    async def me(payload: dict = Depends(get_current_user_payload)):
        return {"sub": payload["sub"]}

    # Admin or Researcher only
    @router.post("/models", dependencies=[Depends(require_roles(UserRole.ADMIN, UserRole.RESEARCHER))])
    async def train_model(...): ...

    # Fine-grained permission
    @router.delete("/datasets/{id}", dependencies=[Depends(require_permission_dep("dataset:delete"))])
    async def delete_dataset(...): ...
"""
from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.constants import TokenType, UserRole
from app.core.jwt_provider import decode_token
from app.core.permissions import has_permission

# ---------------------------------------------------------------------------
# Scheme
# ---------------------------------------------------------------------------

# auto_error=False so we can return 401 (not 403) when the header is absent — RFC 7235
bearer_scheme = HTTPBearer(
    scheme_name="BearerToken",
    description="JWT access token obtained from /api/v1/auth/login",
    auto_error=False,
)

# ---------------------------------------------------------------------------
# Shared 401 factory
# ---------------------------------------------------------------------------

_UNAUTHORIZED = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Invalid or expired token",
    headers={"WWW-Authenticate": "Bearer"},
)

_FORBIDDEN = HTTPException(
    status_code=status.HTTP_403_FORBIDDEN,
    detail="Insufficient permissions",
)


# ---------------------------------------------------------------------------
# Core dependency
# ---------------------------------------------------------------------------


async def get_current_user_payload(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict:
    """
    Extract the Bearer token from the Authorization header, validate it, and
    return the decoded JWT payload.

    This is the base dependency for all authenticated endpoints.  Downstream
    dependencies (``require_roles``, ``require_permission_dep``) build on top
    of it.

    Returns:
        Decoded JWT payload dict (contains at least: sub, jti, type, role, iss, aud).

    Raises:
        HTTPException 401: Token is missing, expired, revoked, or malformed.
    """
    if credentials is None:
        # Missing Authorization header → 401, not 403 (RFC 7235)
        raise _UNAUTHORIZED
    try:
        payload = decode_token(credentials.credentials, TokenType.ACCESS)
    except Exception:
        # Surface all token failures as a uniform 401 — never leak internal detail
        raise _UNAUTHORIZED
    return payload


# ---------------------------------------------------------------------------
# Role-based dependency factory
# ---------------------------------------------------------------------------


def require_roles(*roles: UserRole):
    """
    Return a FastAPI dependency that ensures the authenticated user holds at
    least one of the supplied *roles*.

    Args:
        *roles: One or more ``UserRole`` values.

    Example:
        Depends(require_roles(UserRole.ADMIN, UserRole.RESEARCHER))

    Raises:
        HTTPException 401: Token is invalid.
        HTTPException 403: User's role is not in the allowed set.
    """
    allowed_values = {r.value for r in roles}

    async def _check(
        payload: dict = Depends(get_current_user_payload),
    ) -> dict:
        user_role = payload.get("role")
        if user_role not in allowed_values:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"This action requires one of the following roles: "
                    f"{', '.join(sorted(allowed_values))}"
                ),
            )
        return payload

    return _check


# ---------------------------------------------------------------------------
# Permission-based dependency factory
# ---------------------------------------------------------------------------


def require_permission_dep(permission: str):
    """
    Return a FastAPI dependency that ensures the authenticated user's role
    grants *permission*.

    Args:
        permission: A "<resource>:<action>" string, e.g. "model:write".

    Example:
        Depends(require_permission_dep("dataset:delete"))

    Raises:
        HTTPException 401: Token is invalid.
        HTTPException 403: User's role does not hold *permission*, or the
                           role value in the token is unrecognised.
    """

    async def _check(
        payload: dict = Depends(get_current_user_payload),
    ) -> dict:
        user_role_str = payload.get("role", "")
        try:
            user_role = UserRole(user_role_str)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Unrecognised role: {user_role_str!r}",
            )

        if not has_permission(user_role, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"You do not have permission to perform this action ({permission})",
            )
        return payload

    return _check


# ---------------------------------------------------------------------------
# Optional: get current user without raising on missing token
# ---------------------------------------------------------------------------


async def get_optional_user_payload(
    credentials: HTTPAuthorizationCredentials | None = Depends(
        HTTPBearer(auto_error=False)
    ),
) -> dict | None:
    """
    Like ``get_current_user_payload`` but returns ``None`` instead of raising
    when no token is present.  Useful for endpoints that behave differently
    for authenticated vs anonymous users.
    """
    if credentials is None:
        return None
    try:
        return decode_token(credentials.credentials, TokenType.ACCESS)
    except Exception:
        return None
