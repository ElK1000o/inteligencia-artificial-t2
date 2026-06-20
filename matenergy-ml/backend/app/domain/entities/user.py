from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID
from typing import Optional
from app.core.constants import UserRole


@dataclass
class User:
    id: UUID
    email: str
    username: str
    is_active: bool
    is_superuser: bool
    created_at: datetime
    roles: list[UserRole] = field(default_factory=list)
    failed_login_attempts: int = 0
    locked_until: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def is_locked(self) -> bool:
        if self.locked_until is None:
            return False
        from datetime import timezone
        return datetime.now(tz=timezone.utc) < self.locked_until

    def has_role(self, role: UserRole) -> bool:
        return role in self.roles

    def highest_role(self) -> Optional[UserRole]:
        priority = [UserRole.ADMIN, UserRole.RESEARCHER, UserRole.VIEWER]
        for r in priority:
            if r in self.roles:
                return r
        return None
