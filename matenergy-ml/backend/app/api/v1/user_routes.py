"""
User management routes for MatEnergy-ML.

Endpoints:
  GET    /users                    — list all users (ADMIN)
  GET    /users/me                 — current user profile (any authenticated)
  GET    /users/{user_id}          — user detail (ADMIN or self)
  PUT    /users/{user_id}          — update user (ADMIN or self)
  DELETE /users/{user_id}          — deactivate user (ADMIN)
  GET    /users/{user_id}/audit    — audit log for a user (ADMIN)

Security:
  - Non-admins can only view/update their own profile.
  - Deactivation is soft (is_active=False), never hard-delete.
  - Responses never include hashed_password.
"""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select, func, desc
from sqlalchemy.orm import Session

from app.core.constants import UserRole
from app.core.logging_config import get_logger
from app.core.security import get_current_user_payload, require_roles
from app.infrastructure.database.models.audit_models import AuditLog
from app.infrastructure.database.models.user_models import User, UserRole as UserRoleModel
from app.infrastructure.database.repositories import UserRepository
from app.infrastructure.database.session import get_db
from app.schemas.common import MessageResponse

router = APIRouter(prefix="/users", tags=["users"])
logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Request / Response schemas (local — avoids bloating schemas/)
# ---------------------------------------------------------------------------

class UserProfileResponse(BaseModel):
    id: str
    email: str
    username: str
    is_active: bool
    is_superuser: bool
    roles: list[str]
    created_at: Optional[str]

    class Config:
        from_attributes = True


class UpdateUserRequest(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = None


class AuditLogEntry(BaseModel):
    id: str
    action: str
    resource_type: Optional[str]
    resource_id: Optional[str]
    ip_address: Optional[str]
    status_code: Optional[int]
    created_at: Optional[str]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _user_to_response(user: User, db: Session) -> UserProfileResponse:
    roles = [ur.role.name for ur in user.user_roles if ur.role]
    return UserProfileResponse(
        id=str(user.id),
        email=user.email,
        username=user.username,
        is_active=user.is_active,
        is_superuser=user.is_superuser,
        roles=roles,
        created_at=user.created_at.isoformat() if user.created_at else None,
    )


def _require_admin_or_self(payload: dict, target_user_id: uuid.UUID) -> None:
    requesting_id = uuid.UUID(payload["sub"])
    # JWT payload uses "role" (singular) — set by create_access_token additional_claims
    caller_role = payload.get("role", "")
    if caller_role != UserRole.ADMIN.value and requesting_id != target_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acceso denegado: solo puede acceder a su propio perfil",
        )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/me", response_model=UserProfileResponse)
async def get_my_profile(
    payload: dict = Depends(get_current_user_payload),
    db: Session = Depends(get_db),
) -> UserProfileResponse:
    """Return the profile of the currently authenticated user."""
    user_id = uuid.UUID(payload["sub"])
    repo = UserRepository(db)
    user = repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return _user_to_response(user, db)


@router.get(
    "",
    response_model=list[UserProfileResponse],
    dependencies=[Depends(require_roles(UserRole.ADMIN))],
)
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> list[UserProfileResponse]:
    """List all registered users (ADMIN only)."""
    stmt = select(User).offset(skip).limit(limit).order_by(User.created_at.desc())
    users = list(db.execute(stmt).scalars().all())
    return [_user_to_response(u, db) for u in users]


@router.get("/{user_id}", response_model=UserProfileResponse)
async def get_user(
    user_id: uuid.UUID,
    payload: dict = Depends(get_current_user_payload),
    db: Session = Depends(get_db),
) -> UserProfileResponse:
    """Get user detail. Admins can view any user; others can only view themselves."""
    _require_admin_or_self(payload, user_id)
    repo = UserRepository(db)
    user = repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return _user_to_response(user, db)


@router.put("/{user_id}", response_model=UserProfileResponse)
async def update_user(
    user_id: uuid.UUID,
    body: UpdateUserRequest,
    payload: dict = Depends(get_current_user_payload),
    db: Session = Depends(get_db),
) -> UserProfileResponse:
    """Update user profile. Admins can update any user; others update only themselves."""
    _require_admin_or_self(payload, user_id)
    repo = UserRepository(db)
    user = repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    if body.username is not None:
        # Check uniqueness
        existing = repo.get_by_username(body.username)
        if existing and existing.id != user_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="El nombre de usuario ya está en uso",
            )
        user.username = body.username

    if body.email is not None:
        existing = repo.get_by_email(str(body.email))
        if existing and existing.id != user_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="El correo ya está registrado",
            )
        user.email = str(body.email)

    # Only admins can change is_active
    if body.is_active is not None:
        if payload.get("role") != UserRole.ADMIN.value:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo los administradores pueden cambiar el estado de activación de la cuenta",
            )
        user.is_active = body.is_active

    db.commit()
    db.refresh(user)
    logger.info("user_updated", user_id=str(user_id), updated_by=payload["sub"])
    return _user_to_response(user, db)


@router.delete(
    "/{user_id}",
    response_model=MessageResponse,
    dependencies=[Depends(require_roles(UserRole.ADMIN))],
)
async def deactivate_user(
    user_id: uuid.UUID,
    payload: dict = Depends(get_current_user_payload),
    db: Session = Depends(get_db),
) -> MessageResponse:
    """Soft-deactivate a user account (ADMIN only). Does not hard-delete."""
    requesting_id = uuid.UUID(payload["sub"])
    if requesting_id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No puede desactivar su propia cuenta",
        )
    repo = UserRepository(db)
    user = repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    user.is_active = False
    db.commit()
    logger.info("user_deactivated", user_id=str(user_id), by=str(requesting_id))
    return MessageResponse(message=f"Usuario {user.username} desactivado")


@router.get(
    "/{user_id}/audit",
    response_model=list[AuditLogEntry],
    dependencies=[Depends(require_roles(UserRole.ADMIN))],
)
async def get_user_audit_log(
    user_id: uuid.UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> list[AuditLogEntry]:
    """Return audit log entries for a specific user (ADMIN only)."""
    stmt = (
        select(AuditLog)
        .where(AuditLog.user_id == user_id)
        .order_by(desc(AuditLog.created_at))
        .offset(skip)
        .limit(limit)
    )
    logs = list(db.execute(stmt).scalars().all())
    return [
        AuditLogEntry(
            id=str(log.id),
            action=log.action,
            resource_type=log.resource_type,
            resource_id=str(log.resource_id) if log.resource_id else None,
            ip_address=log.ip_address,
            status_code=log.status_code,
            created_at=log.created_at.isoformat() if log.created_at else None,
        )
        for log in logs
    ]
