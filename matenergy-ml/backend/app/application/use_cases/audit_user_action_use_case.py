"""
AuditUserActionUseCase
======================
Persists a user action to the audit_logs table.

Designed to be called fire-and-forget from API routes after any
significant user operation (upload, train, predict, delete, etc.).
Failures are swallowed with a warning log — audit logging must never
prevent the primary operation from completing.
"""
from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy.orm import Session

from app.core.logging_config import get_logger
from app.infrastructure.database.repositories import AuditLogRepository

logger = get_logger(__name__)


class AuditUserActionUseCase:
    """
    Records user actions for compliance and traceability.

    Args:
        db: Active SQLAlchemy Session.
    """

    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = AuditLogRepository(db)

    def execute(
        self,
        action: str,
        user_id: Optional[uuid.UUID] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[uuid.UUID] = None,
        ip_address: Optional[str] = None,
        status_code: Optional[int] = None,
        metadata: Optional[dict] = None,
    ) -> None:
        """
        Write one audit log entry.

        Args:
            action:        Short snake_case verb describing the operation,
                           e.g. "upload_dataset", "train_model", "delete_user".
            user_id:       UUID of the acting user (None for unauthenticated actions).
            resource_type: Type of the affected resource, e.g. "dataset", "model".
            resource_id:   UUID of the affected resource.
            ip_address:    Client IP (IPv4 or IPv6, max 45 chars).
            status_code:   HTTP status code of the response, if applicable.
            metadata:      Arbitrary structured context (stored as JSONB).
        """
        try:
            self.repo.log_action(
                action=action,
                user_id=user_id,
                resource_type=resource_type,
                resource_id=resource_id,
                ip_address=ip_address,
                status_code=status_code,
                metadata=metadata,
            )
            self.db.commit()
            logger.debug(
                "audit_action_logged",
                action=action,
                user_id=str(user_id) if user_id else None,
                resource_type=resource_type,
            )
        except Exception as exc:
            # Audit logging must never break the main flow
            logger.warning(
                "audit_log_write_failed",
                action=action,
                error=str(exc),
            )
