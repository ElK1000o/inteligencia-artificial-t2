"""Shared pytest fixtures for MatEnergy-ML test suite."""
import uuid
import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

# In-memory SQLite for unit/integration tests (no PostgreSQL needed)
# Note: Some PostgreSQL-specific types (JSONB, UUID) need fallback — we use
# SQLite for speed and PostgreSQL in CI for full fidelity.
import os
os.environ.setdefault("POSTGRES_PASSWORD", "test_password")
os.environ.setdefault("JWT_SECRET_KEY", "test_jwt_secret_key_for_testing_only_32chars")
os.environ.setdefault("ENVIRONMENT", "test")

from app.infrastructure.database.models.base import Base

TEST_DATABASE_URL = "sqlite:///:memory:"

@pytest.fixture(scope="session")
def engine():
    eng = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=eng)
    yield eng
    Base.metadata.drop_all(bind=eng)

@pytest.fixture
def db(engine):
    connection = engine.connect()
    transaction = connection.begin()
    TestSession = sessionmaker(bind=connection)
    session = TestSession()
    yield session
    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture
def sample_formula():
    return "LiFePO4"

@pytest.fixture
def sample_energy_above_hull():
    return 0.001  # eV/atom — stable

@pytest.fixture
def sample_formation_energy():
    return -3.52  # eV/atom — LiFePO4 typical

@pytest.fixture
def sample_band_gap():
    return 3.7  # eV — LiFePO4 typical

@pytest.fixture
def admin_user_id():
    return uuid.uuid4()

@pytest.fixture
def dataset_id():
    return uuid.uuid4()
