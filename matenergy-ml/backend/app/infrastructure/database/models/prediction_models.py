"""
Prediction batch and individual prediction models.

Tables: prediction_batches, predictions
"""
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class PredictionBatch(Base):
    __tablename__ = "prediction_batches"

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
    # pending | running | completed | failed
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    n_materials: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    model_version: Mapped["ModelVersion"] = relationship(  # type: ignore[name-defined]
        "ModelVersion", foreign_keys=[model_version_id]
    )
    dataset: Mapped["Dataset | None"] = relationship(  # type: ignore[name-defined]
        "Dataset", foreign_keys=[dataset_id]
    )
    creator: Mapped["User | None"] = relationship(  # type: ignore[name-defined]
        "User", foreign_keys=[created_by]
    )
    predictions: Mapped[list["Prediction"]] = relationship(
        "Prediction", back_populates="batch", cascade="all, delete-orphan"
    )


class Prediction(Base):
    __tablename__ = "predictions"
    __table_args__ = (
        CheckConstraint(
            "predicted_value IS NOT NULL OR predicted_class IS NOT NULL",
            name="ck_predictions_one_output_not_null",
        ),
        Index("ix_predictions_batch_id", "batch_id"),
        Index("ix_predictions_material_id", "material_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    batch_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("prediction_batches.id", ondelete="CASCADE"),
        nullable=False,
    )
    material_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("materials.id", ondelete="CASCADE"),
        nullable=False,
    )
    predicted_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    predicted_class: Mapped[str | None] = mapped_column(String(255), nullable=True)
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_out_of_domain: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    out_of_domain_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_calibrated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    batch: Mapped["PredictionBatch"] = relationship(
        "PredictionBatch", back_populates="predictions"
    )
    material: Mapped["Material"] = relationship(  # type: ignore[name-defined]
        "Material", foreign_keys=[material_id]
    )
