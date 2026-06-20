"""Repository for background / DFT jobs."""
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.infrastructure.database.models.job_models import BackgroundJob
from app.infrastructure.database.repositories.base_repository import BaseRepository


class JobRepository(BaseRepository[BackgroundJob]):
    def __init__(self, db: Session):
        super().__init__(BackgroundJob, db)

    def list_by_type(
        self,
        job_type: str,
        skip: int = 0,
        limit: int = 50,
    ) -> list[BackgroundJob]:
        stmt = (
            select(BackgroundJob)
            .where(BackgroundJob.job_type == job_type)
            .order_by(BackgroundJob.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(self.db.execute(stmt).scalars().all())

    def list_by_user(
        self,
        user_id: uuid.UUID,
        job_type: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[BackgroundJob]:
        stmt = select(BackgroundJob).where(BackgroundJob.created_by == user_id)
        if job_type:
            stmt = stmt.where(BackgroundJob.job_type == job_type)
        stmt = stmt.order_by(BackgroundJob.created_at.desc()).offset(skip).limit(limit)
        return list(self.db.execute(stmt).scalars().all())

    def mark_running(self, job_id: uuid.UUID) -> Optional[BackgroundJob]:
        job = self.get_by_id(job_id)
        if job:
            job.status = "running"
            job.started_at = datetime.now(timezone.utc)
            self.db.flush()
        return job

    def mark_completed(
        self, job_id: uuid.UUID, result: dict
    ) -> Optional[BackgroundJob]:
        job = self.get_by_id(job_id)
        if job:
            job.status = "completed"
            job.completed_at = datetime.now(timezone.utc)
            job.result = result
            job.progress_pct = 100.0
            self.db.flush()
        return job

    def mark_failed(
        self, job_id: uuid.UUID, error_message: str
    ) -> Optional[BackgroundJob]:
        job = self.get_by_id(job_id)
        if job:
            job.status = "failed"
            job.completed_at = datetime.now(timezone.utc)
            job.error_message = error_message
            self.db.flush()
        return job

    def mark_cancelled(self, job_id: uuid.UUID) -> Optional[BackgroundJob]:
        job = self.get_by_id(job_id)
        if job and job.status in ("pending", "running"):
            job.status = "cancelled"
            job.completed_at = datetime.now(timezone.utc)
            self.db.flush()
        return job
