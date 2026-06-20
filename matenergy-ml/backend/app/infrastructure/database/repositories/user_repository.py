"""User, role and refresh-token repositories."""
import uuid
from typing import Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.infrastructure.database.repositories.base_repository import BaseRepository
from app.infrastructure.database.models.user_models import (
    User, Role, UserRole as UserRoleModel, RefreshToken
)


class UserRepository(BaseRepository[User]):
    def __init__(self, db: Session):
        super().__init__(User, db)

    def get_by_email(self, email: str) -> Optional[User]:
        stmt = select(User).where(User.email == email)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_username(self, username: str) -> Optional[User]:
        stmt = select(User).where(User.username == username)
        return self.db.execute(stmt).scalar_one_or_none()

    def email_exists(self, email: str) -> bool:
        return self.get_by_email(email) is not None

    def increment_failed_attempts(self, user: User) -> None:
        user.failed_login_attempts += 1
        self.db.flush()

    def reset_failed_attempts(self, user: User) -> None:
        user.failed_login_attempts = 0
        user.locked_until = None
        self.db.flush()

    def lock_user(self, user: User, until: datetime) -> None:
        user.locked_until = until
        self.db.flush()

    def get_user_roles(self, user_id: uuid.UUID) -> list[str]:
        stmt = (
            select(Role.name)
            .join(UserRoleModel, Role.id == UserRoleModel.role_id)
            .where(UserRoleModel.user_id == user_id)
        )
        return list(self.db.execute(stmt).scalars().all())

    def assign_role(
        self,
        user_id: uuid.UUID,
        role_id: uuid.UUID,
        assigned_by: Optional[uuid.UUID] = None,
    ) -> None:
        assoc = UserRoleModel(
            id=uuid.uuid4(),
            user_id=user_id,
            role_id=role_id,
            assigned_by=assigned_by,
        )
        self.db.add(assoc)
        self.db.flush()


class RoleRepository(BaseRepository[Role]):
    def __init__(self, db: Session):
        super().__init__(Role, db)

    def get_by_name(self, name: str) -> Optional[Role]:
        stmt = select(Role).where(Role.name == name)
        return self.db.execute(stmt).scalar_one_or_none()


class RefreshTokenRepository(BaseRepository[RefreshToken]):
    def __init__(self, db: Session):
        super().__init__(RefreshToken, db)

    def get_by_jti(self, jti: str) -> Optional[RefreshToken]:
        stmt = select(RefreshToken).where(RefreshToken.jti == jti)
        return self.db.execute(stmt).scalar_one_or_none()

    def revoke(self, token: RefreshToken) -> None:
        from datetime import timezone
        token.is_revoked = True
        token.revoked_at = datetime.now(tz=timezone.utc)
        self.db.flush()

    def revoke_all_for_user(self, user_id: uuid.UUID) -> int:
        from datetime import timezone
        stmt = select(RefreshToken).where(
            RefreshToken.user_id == user_id,
            RefreshToken.is_revoked == False,  # noqa: E712
        )
        tokens = list(self.db.execute(stmt).scalars().all())
        now = datetime.now(tz=timezone.utc)
        for t in tokens:
            t.is_revoked = True
            t.revoked_at = now
        self.db.flush()
        return len(tokens)
