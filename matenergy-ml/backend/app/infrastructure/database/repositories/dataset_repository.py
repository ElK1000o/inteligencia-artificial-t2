"""Dataset, validation-report, rejected-row and uploaded-file repositories."""
import uuid
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from app.infrastructure.database.repositories.base_repository import BaseRepository
from app.infrastructure.database.models.dataset_models import (
    Dataset,
    DatasetValidationReport,
    RejectedDatasetRow,
    UploadedFile,
)


class DatasetRepository(BaseRepository[Dataset]):
    def __init__(self, db: Session):
        super().__init__(Dataset, db)

    def get_by_hash(self, sha256_hash: str) -> Optional[Dataset]:
        stmt = select(Dataset).where(Dataset.sha256_hash == sha256_hash)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_user(
        self, user_id: uuid.UUID, skip: int = 0, limit: int = 50
    ) -> list[Dataset]:
        stmt = (
            select(Dataset)
            .where(Dataset.imported_by == user_id)
            .offset(skip)
            .limit(limit)
        )
        return list(self.db.execute(stmt).scalars().all())

    def get_by_status(self, status: str) -> list[Dataset]:
        stmt = select(Dataset).where(Dataset.status == status)
        return list(self.db.execute(stmt).scalars().all())

    def update_status(self, dataset: Dataset, status: str) -> None:
        dataset.status = status
        self.db.flush()


class DatasetValidationReportRepository(BaseRepository[DatasetValidationReport]):
    def __init__(self, db: Session):
        super().__init__(DatasetValidationReport, db)

    def get_by_dataset(self, dataset_id: uuid.UUID) -> Optional[DatasetValidationReport]:
        stmt = select(DatasetValidationReport).where(
            DatasetValidationReport.dataset_id == dataset_id
        )
        return self.db.execute(stmt).scalar_one_or_none()


class RejectedRowRepository(BaseRepository[RejectedDatasetRow]):
    def __init__(self, db: Session):
        super().__init__(RejectedDatasetRow, db)

    def get_by_dataset(
        self, dataset_id: uuid.UUID, skip: int = 0, limit: int = 100
    ) -> list[RejectedDatasetRow]:
        stmt = (
            select(RejectedDatasetRow)
            .where(RejectedDatasetRow.dataset_id == dataset_id)
            .offset(skip)
            .limit(limit)
        )
        return list(self.db.execute(stmt).scalars().all())

    def count_by_dataset(self, dataset_id: uuid.UUID) -> int:
        stmt = (
            select(func.count())
            .select_from(RejectedDatasetRow)
            .where(RejectedDatasetRow.dataset_id == dataset_id)
        )
        return self.db.execute(stmt).scalar_one()


class UploadedFileRepository(BaseRepository[UploadedFile]):
    def __init__(self, db: Session):
        super().__init__(UploadedFile, db)

    def get_by_stored_filename(self, stored_filename: str) -> Optional[UploadedFile]:
        stmt = select(UploadedFile).where(
            UploadedFile.stored_filename == stored_filename
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_hash(self, sha256_hash: str) -> Optional[UploadedFile]:
        stmt = select(UploadedFile).where(UploadedFile.sha256_hash == sha256_hash)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_user(
        self, user_id: uuid.UUID, skip: int = 0, limit: int = 50
    ) -> list[UploadedFile]:
        stmt = (
            select(UploadedFile)
            .where(UploadedFile.uploaded_by == user_id)
            .offset(skip)
            .limit(limit)
        )
        return list(self.db.execute(stmt).scalars().all())

    def mark_processed(self, file: UploadedFile) -> None:
        file.is_processed = True
        self.db.flush()
