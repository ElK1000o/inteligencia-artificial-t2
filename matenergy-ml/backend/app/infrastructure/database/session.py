"""
SQLAlchemy engine and session factory for MatEnergy-ML.

Usage in FastAPI route handlers:

    from app.infrastructure.database.session import get_db
    from sqlalchemy.orm import Session
    from fastapi import Depends

    def my_endpoint(db: Session = Depends(get_db)):
        ...
"""
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    echo=settings.ENVIRONMENT == "development",
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that yields a database session and guarantees it is
    closed after the request, even on exceptions.
    """
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
