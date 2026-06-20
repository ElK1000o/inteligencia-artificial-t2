"""
Declarative base and shared utilities for SQLAlchemy 2.x models.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""
    pass


def utcnow() -> datetime:
    """Return the current UTC-aware datetime."""
    return datetime.now(tz=timezone.utc)
