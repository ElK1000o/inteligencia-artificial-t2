"""Seed database with initial roles and admin user."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import uuid
from sqlalchemy.orm import Session

from app.infrastructure.database.session import SessionLocal, engine
from app.infrastructure.database.models import Base, Role, User, UserRole as UserRoleModel
from app.core.password_hasher import hash_password
from app.core.constants import UserRole
from app.core.config import settings


def seed(db: Session) -> None:
    # Create roles
    roles_data = [
        (UserRole.ADMIN.value, "Full system administrator with all permissions"),
        (UserRole.RESEARCHER.value, "Can upload data, train models, and generate rankings"),
        (UserRole.VIEWER.value, "Read-only access to results and visualizations"),
    ]
    role_map: dict[str, Role] = {}
    for name, desc in roles_data:
        existing = db.query(Role).filter_by(name=name).first()
        if not existing:
            r = Role(id=uuid.uuid4(), name=name, description=desc)
            db.add(r)
            role_map[name] = r
        else:
            role_map[name] = existing
    db.flush()

    # Create admin user
    admin_email = os.getenv("ADMIN_EMAIL", "admin@matenergy.local")
    admin_password = os.getenv("ADMIN_PASSWORD", "ChangeMe!2025#MatEnergy")
    existing_admin = db.query(User).filter_by(email=admin_email).first()
    if not existing_admin:
        admin = User(
            id=uuid.uuid4(),
            email=admin_email,
            username="admin",
            hashed_password=hash_password(admin_password),
            is_active=True,
            is_superuser=True,
        )
        db.add(admin)
        db.flush()
        assoc = UserRoleModel(
            id=uuid.uuid4(),
            user_id=admin.id,
            role_id=role_map[UserRole.ADMIN.value].id,
        )
        db.add(assoc)
        print(f"Created admin user: {admin_email}")
    else:
        print(f"Admin user already exists: {admin_email}")

    db.commit()
    print("Seed completed successfully.")


if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed(db)
