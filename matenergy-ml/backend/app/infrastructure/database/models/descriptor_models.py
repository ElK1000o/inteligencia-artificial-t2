"""
Feature descriptor models for ML pipelines.

Tables: descriptor_sets, descriptors, descriptor_vectors
"""
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class DescriptorSet(Base):
    __tablename__ = "descriptor_sets"
    __table_args__ = (
        UniqueConstraint("name", "version", name="uq_descriptor_sets_name_version"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    # compositional | structural | combined
    descriptor_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    library_versions: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    feature_names: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    n_features: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    creator: Mapped["User | None"] = relationship(  # type: ignore[name-defined]
        "User", foreign_keys=[created_by]
    )
    descriptors: Mapped[list["Descriptor"]] = relationship(
        "Descriptor", back_populates="descriptor_set", cascade="all, delete-orphan"
    )
    vectors: Mapped[list["DescriptorVector"]] = relationship(
        "DescriptorVector", back_populates="descriptor_set"
    )


class Descriptor(Base):
    __tablename__ = "descriptors"
    __table_args__ = (
        UniqueConstraint(
            "descriptor_set_id", "name",
            name="uq_descriptors_set_name",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    descriptor_set_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("descriptor_sets.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    dtype: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_compositional: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    is_structural: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    # Relationships
    descriptor_set: Mapped["DescriptorSet"] = relationship(
        "DescriptorSet", back_populates="descriptors"
    )


class DescriptorVector(Base):
    __tablename__ = "descriptor_vectors"
    __table_args__ = (
        UniqueConstraint(
            "material_id", "descriptor_set_id",
            name="uq_descriptor_vectors_material_set",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    material_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("materials.id", ondelete="CASCADE"),
        nullable=False,
    )
    descriptor_set_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("descriptor_sets.id", ondelete="CASCADE"),
        nullable=False,
    )
    # Stored as a JSON array of floats
    vector: Mapped[dict] = mapped_column(JSONB, nullable=False)
    has_nan: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    nan_features: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    material: Mapped["Material"] = relationship(  # type: ignore[name-defined]
        "Material", foreign_keys=[material_id]
    )
    descriptor_set: Mapped["DescriptorSet"] = relationship(
        "DescriptorSet", back_populates="vectors"
    )
