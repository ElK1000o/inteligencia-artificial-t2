"""ML model versioning, artifact, training-run, metric and parameter repositories."""
import uuid
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.infrastructure.database.repositories.base_repository import BaseRepository
from app.infrastructure.database.models.model_models import (
    ModelVersion,
    ModelArtifact,
    ModelTrainingRun,
    ModelMetric,
    ModelParameter,
)


class ModelVersionRepository(BaseRepository[ModelVersion]):
    def __init__(self, db: Session):
        super().__init__(ModelVersion, db)

    def get_active_for_target(self, target_property: str) -> Optional[ModelVersion]:
        stmt = (
            select(ModelVersion)
            .where(
                ModelVersion.target_property == target_property,
                ModelVersion.is_active == True,  # noqa: E712
            )
            .limit(1)
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def deactivate_all_for_target(self, target_property: str) -> None:
        stmt = select(ModelVersion).where(
            ModelVersion.target_property == target_property,
            ModelVersion.is_active == True,  # noqa: E712
        )
        versions = list(self.db.execute(stmt).scalars().all())
        for v in versions:
            v.is_active = False
        self.db.flush()

    def activate(self, model_version: ModelVersion) -> None:
        """Deactivate all versions for the same target, then mark this one active."""
        self.deactivate_all_for_target(model_version.target_property)
        model_version.is_active = True
        self.db.flush()

    def get_by_model_type(self, model_type: str) -> list[ModelVersion]:
        stmt = select(ModelVersion).where(ModelVersion.model_type == model_type)
        return list(self.db.execute(stmt).scalars().all())

    def get_by_dataset(self, dataset_id: uuid.UUID) -> list[ModelVersion]:
        stmt = select(ModelVersion).where(ModelVersion.dataset_id == dataset_id)
        return list(self.db.execute(stmt).scalars().all())


class ModelArtifactRepository(BaseRepository[ModelArtifact]):
    def __init__(self, db: Session):
        super().__init__(ModelArtifact, db)

    def get_by_model_version(
        self, model_version_id: uuid.UUID
    ) -> Optional[ModelArtifact]:
        stmt = select(ModelArtifact).where(
            ModelArtifact.model_version_id == model_version_id
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_hash(self, sha256_hash: str) -> Optional[ModelArtifact]:
        stmt = select(ModelArtifact).where(ModelArtifact.sha256_hash == sha256_hash)
        return self.db.execute(stmt).scalar_one_or_none()


class ModelTrainingRunRepository(BaseRepository[ModelTrainingRun]):
    def __init__(self, db: Session):
        super().__init__(ModelTrainingRun, db)

    def get_by_model_version(
        self, model_version_id: uuid.UUID
    ) -> list[ModelTrainingRun]:
        stmt = select(ModelTrainingRun).where(
            ModelTrainingRun.model_version_id == model_version_id
        )
        return list(self.db.execute(stmt).scalars().all())

    def get_latest_completed(
        self, model_version_id: uuid.UUID
    ) -> Optional[ModelTrainingRun]:
        stmt = (
            select(ModelTrainingRun)
            .where(
                ModelTrainingRun.model_version_id == model_version_id,
                ModelTrainingRun.status == "completed",
            )
            .order_by(ModelTrainingRun.completed_at.desc())
            .limit(1)
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_status(self, status: str) -> list[ModelTrainingRun]:
        stmt = select(ModelTrainingRun).where(ModelTrainingRun.status == status)
        return list(self.db.execute(stmt).scalars().all())


class ModelMetricRepository(BaseRepository[ModelMetric]):
    def __init__(self, db: Session):
        super().__init__(ModelMetric, db)

    def get_by_run(self, training_run_id: uuid.UUID) -> list[ModelMetric]:
        stmt = select(ModelMetric).where(
            ModelMetric.training_run_id == training_run_id
        )
        return list(self.db.execute(stmt).scalars().all())

    def get_test_metrics(self, training_run_id: uuid.UUID) -> list[ModelMetric]:
        stmt = select(ModelMetric).where(
            ModelMetric.training_run_id == training_run_id,
            ModelMetric.split == "test",
        )
        return list(self.db.execute(stmt).scalars().all())

    def get_by_metric_name(
        self, training_run_id: uuid.UUID, metric_name: str
    ) -> list[ModelMetric]:
        stmt = select(ModelMetric).where(
            ModelMetric.training_run_id == training_run_id,
            ModelMetric.metric_name == metric_name,
        )
        return list(self.db.execute(stmt).scalars().all())


class ModelParameterRepository(BaseRepository[ModelParameter]):
    def __init__(self, db: Session):
        super().__init__(ModelParameter, db)

    def get_by_model_version(
        self, model_version_id: uuid.UUID
    ) -> list[ModelParameter]:
        stmt = select(ModelParameter).where(
            ModelParameter.model_version_id == model_version_id
        )
        return list(self.db.execute(stmt).scalars().all())

    def get_by_name(
        self, model_version_id: uuid.UUID, parameter_name: str
    ) -> Optional[ModelParameter]:
        stmt = select(ModelParameter).where(
            ModelParameter.model_version_id == model_version_id,
            ModelParameter.parameter_name == parameter_name,
        )
        return self.db.execute(stmt).scalar_one_or_none()
