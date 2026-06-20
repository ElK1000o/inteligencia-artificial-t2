"""Integration tests: SQLAlchemy repository CRUD operations (SQLite in-memory)."""
import uuid
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.infrastructure.database.models.base import Base
from app.infrastructure.database.models.user_models import User, Role, UserRole
from app.infrastructure.database.repositories.user_repository import UserRepository, RoleRepository


TEST_DB_URL = "sqlite:///:memory:"


@pytest.fixture(scope="module")
def engine():
    eng = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=eng)
    yield eng
    Base.metadata.drop_all(bind=eng)


@pytest.fixture
def db(engine):
    conn = engine.connect()
    txn = conn.begin()
    Session = sessionmaker(bind=conn)
    session = Session()
    yield session
    session.close()
    txn.rollback()
    conn.close()


class TestUserRepository:
    def test_create_and_get_user(self, db):
        repo = UserRepository(db)
        user_id = uuid.uuid4()
        user = User(
            id=user_id,
            email="test@example.com",
            username="testuser",
            hashed_password="$argon2id$v=19$m=65536,t=3,p=4$fake",
            is_active=True,
            is_superuser=False,
            failed_login_attempts=0,
        )
        db.add(user)
        db.flush()

        found = repo.get_by_id(user_id)
        assert found is not None
        assert found.email == "test@example.com"

    def test_get_by_email_returns_user(self, db):
        repo = UserRepository(db)
        user = User(
            id=uuid.uuid4(),
            email="unique@example.com",
            username="uniqueuser",
            hashed_password="hash",
            is_active=True,
            is_superuser=False,
            failed_login_attempts=0,
        )
        db.add(user)
        db.flush()

        found = repo.get_by_email("unique@example.com")
        assert found is not None
        assert found.username == "uniqueuser"

    def test_get_by_email_nonexistent_returns_none(self, db):
        repo = UserRepository(db)
        result = repo.get_by_email("doesnotexist@nowhere.com")
        assert result is None

    def test_get_by_id_nonexistent_returns_none(self, db):
        repo = UserRepository(db)
        result = repo.get_by_id(uuid.uuid4())
        assert result is None

    def test_failed_login_attempts_incremented(self, db):
        repo = UserRepository(db)
        user = User(
            id=uuid.uuid4(),
            email="bruteforce@example.com",
            username="bruteforceuser",
            hashed_password="hash",
            is_active=True,
            is_superuser=False,
            failed_login_attempts=0,
        )
        db.add(user)
        db.flush()

        user.failed_login_attempts += 1
        db.flush()

        found = repo.get_by_email("bruteforce@example.com")
        assert found.failed_login_attempts == 1


class TestRoleRepository:
    def test_get_by_name_returns_role(self, db):
        repo = RoleRepository(db)
        role = Role(id=uuid.uuid4(), name="test_role", description="A test role")
        db.add(role)
        db.flush()

        found = repo.get_by_name("test_role")
        assert found is not None
        assert found.description == "A test role"

    def test_get_by_name_nonexistent_returns_none(self, db):
        repo = RoleRepository(db)
        result = repo.get_by_name("nonexistent_role_xyz")
        assert result is None
