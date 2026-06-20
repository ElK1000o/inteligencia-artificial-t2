"""
ML model versioning, artifacts, training runs, metrics and parameters.

Tables: model_versions, model_artifacts, model_training_runs,
        model_metrics, model_parameters
"""
import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class ModelVersion(Base):
    __tablename__ = "model_versions"
    __table_args__ = (
        Index(
            "ix_model_versions_type_property_active",
            "model_type", "target_property", "is_active",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    # e.g. random_forest, gradient_boosting, neural_network, gaussian_process
    model_type: Mapped[str] = mapped_column(String(100), nullable=False)
    # regression | classification
    task_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    target_property: Mapped[str] = mapped_column(String(255), nullable=False)
    descriptor_set_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("descriptor_sets.id", ondelete="SET NULL"),
        nullable=True,
    )
    dataset_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("datasets.id", ondelete="SET NULL"),
        nullable=True,
    )
    version_tag: Mapped[str | None] = mapped_column(String(50), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    descriptor_set: Mapped["DescriptorSet | None"] = relationship(  # type: ignore[name-defined]
        "DescriptorSet", foreign_keys=[descriptor_set_id]
    )
    dataset: Mapped["Dataset | None"] = relationship(  # type: ignore[name-defined]
        "Dataset", foreign_keys=[dataset_id]
    )
    creator: Mapped["User | None"] = relationship(  # type: ignore[name-defined]
        "User", foreign_keys=[created_by]
    )
    artifact: Mapped["ModelArtifact | None"] = relationship(
        "ModelArtifact", back_populates="model_version", uselist=False
    )
    training_runs: Mapped[list["ModelTrainingRun"]] = relationship(
        "ModelTrainingRun", back_populates="model_version"
    )
    parameters: Mapped[list["ModelParameter"]] = relationship(
        "ModelParameter", back_populates="model_version", cascade="all, delete-orphan"
    )


class ModelArtifact(Base):
    """
    Serialised model file.
    ALWAYS verify sha256_hash before loading the artifact from disk.
    """
    __tablename__ = "model_artifacts"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    model_version_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("model_versions.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    sha256_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    file_size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    # sklearn_joblib | onnx | pytorch | tensorflow | custom
    artifact_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    serialization_format: Mapped[str | None] = mapped_column(String(50), nullable=True)
    python_version: Mapped[str | None] = mapped_column(String(20), nullable=True)
    library_versions: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    model_version: Mapped["ModelVersion"] = relationship(
        "ModelVersion", back_populates="artifact"
    )


class ModelTrainingRun(Base):
    __tablename__ = "model_training_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    model_version_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("model_versions.id", ondelete="CASCADE"),
        nullable=False,
    )
    dataset_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("datasets.id", ondelete="SET NULL"),
        nullable=True,
    )
    descriptor_set_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("descriptor_sets.id", ondelete="SET NULL"),
        nullable=True,
    )
    # running | completed | failed
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="running")
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    n_train_samples: Mapped[int | None] = mapped_column(Integer, nullable=True)
    n_test_samples: Mapped[int | None] = mapped_column(Integer, nullable=True)
    n_features: Mapped[int | None] = mapped_column(Integer, nullable=True)
    random_seed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    hyperparameters: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    triggered_by: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    model_version: Mapped["ModelVersion"] = relationship(
        "ModelVersion", back_populates="training_runs"
    )
    dataset: Mapped["Dataset | None"] = relationship(  # type: ignore[name-defined]
        "Dataset", foreign_keys=[dataset_id]
    )
    descriptor_set: Mapped["DescriptorSet | None"] = relationship(  # type: ignore[name-defined]
        "DescriptorSet", foreign_keys=[descriptor_set_id]
    )
    trigger_user: Mapped["User | None"] = relationship(  # type: ignore[name-defined]
        "User", foreign_keys=[triggered_by]
    )
    metrics: Mapped[list["ModelMetric"]] = relationship(
        "ModelMetric", back_populates="training_run", cascade="all, delete-orphan"
    )


class ModelMetric(Base):
    __tablename__ = "model_metrics"
    __table_args__ = (
        UniqueConstraint(
            "training_run_id", "split", "metric_name",
            name="uq_model_metrics_run_split_metric",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    training_run_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("model_training_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    # train | test | cv
    split: Mapped[str] = mapped_column(String(20), nullable=False)
    metric_name: Mapped[str] = mapped_column(String(100), nullable=False)
    metric_value: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    training_run: Mapped["ModelTrainingRun"] = relationship(
        "ModelTrainingRun", back_populates="metrics"
    )


class ModelParameter(Base):
    __tablename__ = "model_parameters"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    model_version_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("model_versions.id", ondelete="CASCADE"),
        nullable=False,
    )
    parameter_name: Mapped[str] = mapped_column(String(255), nullable=False)
    parameter_value: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    model_version: Mapped["ModelVersion"] = relationship(
        "ModelVersion", back_populates="parameters"
    )
