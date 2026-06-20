"""
Audit logger for MatEnergy-ML.
Logs user actions and security events to the database.
"""
import uuid
from typing import Optional
from sqlalchemy.orm import Session
from app.infrastructure.database.repositories import AuditLogRepository, SecurityEventRepository
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class AuditLogger:
    """Service for logging audit events and security events to the database."""

    def __init__(self, db: Session):
        self.db = db
        self.audit_repo = AuditLogRepository(db)
        self.security_repo = SecurityEventRepository(db)

    def log_action(
        self,
        action: str,
        user_id: Optional[uuid.UUID] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[uuid.UUID] = None,
        ip_address: Optional[str] = None,
        status_code: Optional[int] = None,
        metadata: Optional[dict] = None,
    ) -> None:
        try:
            self.audit_repo.log_action(
                action=action,
                user_id=user_id,
                resource_type=resource_type,
                resource_id=resource_id,
                ip_address=ip_address,
                status_code=status_code,
                metadata=metadata,
            )
        except Exception as e:
            logger.error("audit_log_failed", action=action, error=str(e))

    def log_security_event(
        self,
        event_type: str,
        severity: str,
        description: str,
        user_id: Optional[uuid.UUID] = None,
        ip_address: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> None:
        try:
            self.security_repo.log_event(
                event_type=event_type,
                severity=severity,
                description=description,
                user_id=user_id,
                ip_address=ip_address,
                metadata=metadata,
            )
            logger.warning(
                "security_event",
                event_type=event_type,
                severity=severity,
                description=description[:100],
            )
        except Exception as e:
            logger.error("security_event_log_failed", event_type=event_type, error=str(e))
