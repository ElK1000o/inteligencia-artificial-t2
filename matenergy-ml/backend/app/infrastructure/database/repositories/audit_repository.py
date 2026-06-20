"""Audit log and security event repositories."""
import uuid
from typing import Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import select, func, desc

from app.infrastructure.database.repositories.base_repository import BaseRepository
from app.infrastructure.database.models.audit_models import AuditLog, SecurityEvent


class AuditLogRepository(BaseRepository[AuditLog]):
    def __init__(self, db: Session):
        super().__init__(AuditLog, db)

    def log_action(
        self,
        action: str,
        user_id: Optional[uuid.UUID] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[uuid.UUID] = None,
        ip_address: Optional[str] = None,
        status_code: Optional[int] = None,
        metadata: Optional[dict] = None,
    ) -> AuditLog:
        entry = AuditLog(
            id=uuid.uuid4(),
            action=action,
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            status_code=status_code,
            metadata_=metadata,
        )
        self.db.add(entry)
        self.db.flush()
        return entry

    def get_by_user(
        self, user_id: uuid.UUID, skip: int = 0, limit: int = 100
    ) -> list[AuditLog]:
        stmt = (
            select(AuditLog)
            .where(AuditLog.user_id == user_id)
            .order_by(desc(AuditLog.created_at))
            .offset(skip)
            .limit(limit)
        )
        return list(self.db.execute(stmt).scalars().all())

    def get_by_resource(
        self, resource_type: str, resource_id: uuid.UUID
    ) -> list[AuditLog]:
        stmt = (
            select(AuditLog)
            .where(
                AuditLog.resource_type == resource_type,
                AuditLog.resource_id == resource_id,
            )
            .order_by(desc(AuditLog.created_at))
        )
        return list(self.db.execute(stmt).scalars().all())

    def get_by_action(
        self, action: str, skip: int = 0, limit: int = 100
    ) -> list[AuditLog]:
        stmt = (
            select(AuditLog)
            .where(AuditLog.action == action)
            .order_by(desc(AuditLog.created_at))
            .offset(skip)
            .limit(limit)
        )
        return list(self.db.execute(stmt).scalars().all())

    def count_by_action(self, action: str) -> int:
        stmt = (
            select(func.count())
            .select_from(AuditLog)
            .where(AuditLog.action == action)
        )
        return self.db.execute(stmt).scalar_one()


class SecurityEventRepository(BaseRepository[SecurityEvent]):
    def __init__(self, db: Session):
        super().__init__(SecurityEvent, db)

    def log_event(
        self,
        event_type: str,
        severity: str,
        description: str,
        user_id: Optional[uuid.UUID] = None,
        ip_address: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> SecurityEvent:
        event = SecurityEvent(
            id=uuid.uuid4(),
            event_type=event_type,
            severity=severity,
            description=description,
            user_id=user_id,
            ip_address=ip_address,
            metadata_=metadata,
        )
        self.db.add(event)
        self.db.flush()
        return event

    def get_unresolved(self, skip: int = 0, limit: int = 50) -> list[SecurityEvent]:
        stmt = (
            select(SecurityEvent)
            .where(SecurityEvent.resolved == False)  # noqa: E712
            .order_by(desc(SecurityEvent.created_at))
            .offset(skip)
            .limit(limit)
        )
        return list(self.db.execute(stmt).scalars().all())

    def get_by_severity(
        self, severity: str, skip: int = 0, limit: int = 50
    ) -> list[SecurityEvent]:
        stmt = (
            select(SecurityEvent)
            .where(SecurityEvent.severity == severity)
            .order_by(desc(SecurityEvent.created_at))
            .offset(skip)
            .limit(limit)
        )
        return list(self.db.execute(stmt).scalars().all())

    def count_by_severity(self, severity: str) -> int:
        stmt = (
            select(func.count())
            .select_from(SecurityEvent)
            .where(
                SecurityEvent.severity == severity,
                SecurityEvent.resolved == False,  # noqa: E712
            )
        )
        return self.db.execute(stmt).scalar_one()

    def resolve(self, event: SecurityEvent) -> None:
        from datetime import timezone
        event.resolved = True
        event.resolved_at = datetime.now(tz=timezone.utc)
        self.db.flush()

    def get_by_user(
        self, user_id: uuid.UUID, skip: int = 0, limit: int = 50
    ) -> list[SecurityEvent]:
        stmt = (
            select(SecurityEvent)
            .where(SecurityEvent.user_id == user_id)
            .order_by(desc(SecurityEvent.created_at))
            .offset(skip)
            .limit(limit)
        )
        return list(self.db.execute(stmt).scalars().all())
