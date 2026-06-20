"""
Dataset ingestion, validation, and file-upload models.

Tables: data_sources, datasets, dataset_columns, dataset_validation_reports,
        rejected_dataset_rows, uploaded_files
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


class DataSource(Base):
    __tablename__ = "data_sources"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    # csv_local | materials_project | jarvis | nomad | aflow | oqmd | custom
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    base_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    requires_api_key: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    datasets: Mapped[list["Dataset"]] = relationship(
        "Dataset", back_populates="source"
    )


class Dataset(Base):
    __tablename__ = "datasets"
    __table_args__ = (
        Index("ix_datasets_sha256_hash", "sha256_hash"),
        Index("ix_datasets_imported_by", "imported_by"),
        Index("ix_datasets_status", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("data_sources.id", ondelete="SET NULL"),
        nullable=True,
    )
    file_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    sha256_hash: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False
    )
    row_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    valid_row_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rejected_row_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    column_names: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    available_properties: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    imported_by: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    imported_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # pending | validating | valid | invalid | partial
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    metadata_: Mapped[dict | None] = mapped_column(
        "metadata", JSONB, nullable=True
    )

    # Relationships
    source: Mapped["DataSource | None"] = relationship(
        "DataSource", back_populates="datasets"
    )
    importer: Mapped["User | None"] = relationship(  # type: ignore[name-defined]
        "User", foreign_keys=[imported_by]
    )
    columns: Mapped[list["DatasetColumn"]] = relationship(
        "DatasetColumn", back_populates="dataset", cascade="all, delete-orphan"
    )
    validation_report: Mapped["DatasetValidationReport | None"] = relationship(
        "DatasetValidationReport", back_populates="dataset", uselist=False
    )
    rejected_rows: Mapped[list["RejectedDatasetRow"]] = relationship(
        "RejectedDatasetRow", back_populates="dataset", cascade="all, delete-orphan"
    )


class DatasetColumn(Base):
    __tablename__ = "dataset_columns"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    dataset_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("datasets.id", ondelete="CASCADE"),
        nullable=False,
    )
    column_name: Mapped[str] = mapped_column(String(255), nullable=False)
    data_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_required: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    unit: Mapped[str | None] = mapped_column(String(50), nullable=True)
    min_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    null_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    unique_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Relationships
    dataset: Mapped["Dataset"] = relationship("Dataset", back_populates="columns")


class DatasetValidationReport(Base):
    __tablename__ = "dataset_validation_reports"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    dataset_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("datasets.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    total_rows: Mapped[int | None] = mapped_column(Integer, nullable=True)
    valid_rows: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rejected_rows: Mapped[int | None] = mapped_column(Integer, nullable=True)
    validation_errors: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    warnings: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    validation_rules_applied: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    validated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    validated_by: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Relationships
    dataset: Mapped["Dataset"] = relationship(
        "Dataset", back_populates="validation_report"
    )
    validator: Mapped["User | None"] = relationship(  # type: ignore[name-defined]
        "User", foreign_keys=[validated_by]
    )


class RejectedDatasetRow(Base):
    __tablename__ = "rejected_dataset_rows"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    dataset_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("datasets.id", ondelete="CASCADE"),
        nullable=False,
    )
    row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    raw_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    rejection_reasons: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    rejected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    dataset: Mapped["Dataset"] = relationship(
        "Dataset", back_populates="rejected_rows"
    )


class UploadedFile(Base):
    """
    Records of files uploaded by users.
    NEVER store original_filename as a path — only stored_filename / stored_path are
    used for filesystem access.
    """
    __tablename__ = "uploaded_files"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # Display-only; never used to locate the file on disk.
    original_filename: Mapped[str | None] = mapped_column(Text, nullable=True)
    stored_filename: Mapped[str] = mapped_column(
        Text, unique=True, nullable=False
    )
    stored_path: Mapped[str] = mapped_column(Text, nullable=False)
    sha256_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(127), nullable=True)
    file_size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    uploaded_by: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    is_processed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Relationships
    uploader: Mapped["User | None"] = relationship(  # type: ignore[name-defined]
        "User", foreign_keys=[uploaded_by]
    )
