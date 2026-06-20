"""
Authentication routes for MatEnergy-ML.

Endpoints:
  POST /auth/login     — issue access + refresh tokens
  POST /auth/refresh   — rotate refresh token
  POST /auth/logout    — revoke refresh token (requires auth)
  POST /auth/register  — create user (ADMIN only, or first user bootstrap)
  GET  /auth/me        — return current user profile (requires auth)

Security notes:
  - Login errors are intentionally generic to prevent account enumeration.
  - After MAX_LOGIN_ATTEMPTS failures the account is locked for LOCKOUT_MINUTES.
  - Refresh-token rotation: old token is revoked and a new pair is issued atomically.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.constants import TokenType, UserRole
from app.core.jwt_provider import create_access_token, create_refresh_token, decode_token
from app.core.logging_config import get_logger
from app.core.password_hasher import hash_password, needs_rehash, verify_password
from app.core.security import get_current_user_payload, require_roles
from app.infrastructure.database.models.user_models import RefreshToken
from app.infrastructure.database.repositories.user_repository import (
    RefreshTokenRepository,
    RoleRepository,
    UserRepository,
)
from app.infrastructure.database.session import get_db
from app.schemas.auth_schemas import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.schemas.common import MessageResponse

router = APIRouter(prefix="/auth", tags=["auth"])
logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_GENERIC_AUTH_ERROR = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Credenciales inválidas",
    headers={"WWW-Authenticate": "Bearer"},
)


def _build_token_response(user_id: str, roles: list[str], db: Session) -> TokenResponse:
    """Create an access + refresh token pair and persist the refresh token."""
    highest_role = roles[0] if roles else UserRole.VIEWER.value
    access_token = create_access_token(
        user_id, additional_claims={"role": highest_role}
    )
    refresh_str, jti = create_refresh_token(user_id)

    rt = RefreshToken(
        id=uuid.uuid4(),
        jti=jti,
        user_id=uuid.UUID(user_id),
        expires_at=datetime.now(tz=timezone.utc)
        + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )
    db.add(rt)
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_str,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post("/login", response_model=TokenResponse)
async def login(
    request: Request,
    body: LoginRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """Exchange email + password for JWT tokens."""
    user_repo = UserRepository(db)

    user = user_repo.get_by_email(body.email)
    if not user:
        logger.warning(
            "login_failed_unknown_email",
            ip=request.client.host if request.client else "unknown",
        )
        raise _GENERIC_AUTH_ERROR

    # Account lock check
    if user.locked_until and user.locked_until > datetime.now(tz=timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Cuenta bloqueada temporalmente. Inténtelo nuevamente más tarde.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise _GENERIC_AUTH_ERROR

    if not verify_password(body.password, user.hashed_password):
        user_repo.increment_failed_attempts(user)
        if user.failed_login_attempts >= settings.MAX_LOGIN_ATTEMPTS:
            lock_until = datetime.now(tz=timezone.utc) + timedelta(
                minutes=settings.LOGIN_LOCKOUT_MINUTES
            )
            user_repo.lock_user(user, lock_until)
            logger.warning(
                "account_locked",
                user_id=str(user.id),
                lock_until=lock_until.isoformat(),
            )
        db.commit()
        raise _GENERIC_AUTH_ERROR

    # Successful login — reset failure counter
    user_repo.reset_failed_attempts(user)

    # Optionally rehash if parameters changed
    if needs_rehash(user.hashed_password):
        user.hashed_password = hash_password(body.password)

    roles = user_repo.get_user_roles(user.id)
    token_response = _build_token_response(str(user.id), roles, db)
    db.commit()

    logger.info(
        "login_success",
        user_id=str(user.id),
        ip=request.client.host if request.client else "unknown",
    )
    return token_response


@router.post("/refresh", response_model=TokenResponse)
async def refresh_tokens(
    body: RefreshRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """Rotate a refresh token: revoke the old one and issue a new pair."""
    refresh_repo = RefreshTokenRepository(db)
    user_repo = UserRepository(db)

    try:
        rt_payload = decode_token(body.refresh_token, TokenType.REFRESH)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de actualización inválido",
            headers={"WWW-Authenticate": "Bearer"},
        )

    jti = rt_payload.get("jti")
    stored = refresh_repo.get_by_jti(jti)
    if not stored or stored.is_revoked:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="El token de actualización fue revocado o no existe",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Revoke old token (rotation)
    refresh_repo.revoke(stored)

    user = user_repo.get_by_id(uuid.UUID(rt_payload["sub"]))
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado o inactivo",
            headers={"WWW-Authenticate": "Bearer"},
        )

    roles = user_repo.get_user_roles(user.id)
    token_response = _build_token_response(str(user.id), roles, db)
    db.commit()
    return token_response


@router.post("/logout", response_model=MessageResponse)
async def logout(
    body: RefreshRequest,
    payload: dict = Depends(get_current_user_payload),
    db: Session = Depends(get_db),
) -> MessageResponse:
    """Revoke the provided refresh token. Idempotent — already-revoked tokens are accepted."""
    refresh_repo = RefreshTokenRepository(db)
    try:
        rt_payload = decode_token(body.refresh_token, TokenType.REFRESH)
        jti = rt_payload.get("jti")
        stored = refresh_repo.get_by_jti(jti)
        if stored and not stored.is_revoked:
            refresh_repo.revoke(stored)
            db.commit()
    except Exception:
        # Token already invalid — silently accept logout
        pass

    logger.info("logout", user_id=payload.get("sub"))
    return MessageResponse(message="Sesión cerrada correctamente")


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    request: Request,
    body: RegisterRequest,
    db: Session = Depends(get_db),
) -> UserResponse:
    """
    Register a new user.

    Access rules:
    - Allowed when there are zero existing users (bootstrap mode).
    - Otherwise requires a valid ADMIN-role JWT in the Authorization header.
    """
    from app.infrastructure.database.models.user_models import User
    from app.core.constants import TokenType
    from app.core.jwt_provider import decode_token

    user_repo = UserRepository(db)
    role_repo = RoleRepository(db)

    # Bootstrap: if no users exist yet, allow unauthenticated registration
    total_users = user_repo.count()

    if total_users > 0:
        # After bootstrap, only ADMIN may create new users
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Se requiere autenticación para registrar nuevos usuarios",
                headers={"WWW-Authenticate": "Bearer"},
            )
        token = auth_header.removeprefix("Bearer ").strip()
        try:
            token_payload = decode_token(token, TokenType.ACCESS)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido o expirado",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if token_payload.get("role") != UserRole.ADMIN.value:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo los administradores pueden registrar nuevos usuarios",
            )

    # Duplicate checks
    if user_repo.email_exists(body.email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El correo ya está registrado",
        )
    if user_repo.get_by_username(body.username):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El nombre de usuario ya está en uso",
        )

    hashed = hash_password(body.password)
    new_user = User(
        id=uuid.uuid4(),
        email=body.email,
        username=body.username,
        hashed_password=hashed,
        is_active=True,
        is_superuser=(total_users == 0),  # first user gets superuser
    )
    db.add(new_user)
    db.flush()

    # Assign default role
    default_role_name = UserRole.ADMIN.value if total_users == 0 else UserRole.VIEWER.value
    role = role_repo.get_by_name(default_role_name)
    if role:
        user_repo.assign_role(new_user.id, role.id)

    db.commit()
    db.refresh(new_user)

    roles = user_repo.get_user_roles(new_user.id)
    logger.info("user_registered", user_id=str(new_user.id), is_bootstrap=(total_users == 0))
    return UserResponse(
        id=new_user.id,
        email=new_user.email,
        username=new_user.username,
        is_active=new_user.is_active,
        roles=roles,
    )


@router.get("/me", response_model=UserResponse)
async def get_me(
    payload: dict = Depends(get_current_user_payload),
    db: Session = Depends(get_db),
) -> UserResponse:
    """Return the profile of the currently authenticated user."""
    user_repo = UserRepository(db)
    user = user_repo.get_by_id(uuid.UUID(payload["sub"]))
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")

    roles = user_repo.get_user_roles(user.id)
    return UserResponse(
        id=user.id,
        email=user.email,
        username=user.username,
        is_active=user.is_active,
        roles=roles,
    )
