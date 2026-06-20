"""
Materials, compositions, properties and crystal-structure models.

Tables: materials, material_compositions, material_properties, material_structures
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
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class Material(Base):
    __tablename__ = "materials"
    __table_args__ = (
        UniqueConstraint("formula", "dataset_id", name="uq_materials_formula_dataset"),
        CheckConstraint("nelements >= 1", name="ck_materials_nelements_positive"),
        Index("ix_materials_formula", "formula"),
        Index("ix_materials_reduced_formula", "reduced_formula"),
        Index("ix_materials_chemsys", "chemsys"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    formula: Mapped[str] = mapped_column(String(255), nullable=False)
    reduced_formula: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Sorted, hyphen-separated element symbols, e.g. "Fe-Li-O"
    chemsys: Mapped[str | None] = mapped_column(String(255), nullable=True)
    dataset_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("datasets.id", ondelete="SET NULL"),
        nullable=True,
    )
    # External identifier in Materials Project, JARVIS, AFLOW, etc.
    source_material_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    nelements: Mapped[int | None] = mapped_column(Integer, nullable=True)
    elements: Mapped[dict | None] = mapped_column(JSONB, nullable=True)  # list of symbols
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), nullable=True
    )

    # Relationships
    dataset: Mapped["Dataset | None"] = relationship(  # type: ignore[name-defined]
        "Dataset", foreign_keys=[dataset_id]
    )
    compositions: Mapped[list["MaterialComposition"]] = relationship(
        "MaterialComposition", back_populates="material", cascade="all, delete-orphan"
    )
    properties: Mapped[list["MaterialProperty"]] = relationship(
        "MaterialProperty", back_populates="material", cascade="all, delete-orphan"
    )
    structure: Mapped["MaterialStructure | None"] = relationship(
        "MaterialStructure", back_populates="material", uselist=False
    )


class MaterialComposition(Base):
    __tablename__ = "material_compositions"
    __table_args__ = (
        UniqueConstraint(
            "material_id", "element_symbol",
            name="uq_material_compositions_material_element",
        ),
        CheckConstraint(
            "fraction >= 0 AND fraction <= 1",
            name="ck_material_compositions_fraction_range",
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
    element_symbol: Mapped[str] = mapped_column(String(3), nullable=False)
    fraction: Mapped[float] = mapped_column(Float, nullable=False)

    # Relationships
    material: Mapped["Material"] = relationship(
        "Material", back_populates="compositions"
    )


class MaterialProperty(Base):
    __tablename__ = "material_properties"
    __table_args__ = (
        UniqueConstraint(
            "material_id", "property_name",
            name="uq_material_properties_material_property",
        ),
        CheckConstraint(
            "value_float IS NOT NULL OR value_str IS NOT NULL OR value_bool IS NOT NULL",
            name="ck_material_properties_one_value_not_null",
        ),
        Index("ix_material_properties_material_id", "material_id"),
        Index("ix_material_properties_property_name", "property_name"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    material_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("materials.id", ondelete="CASCADE"),
        nullable=False,
    )
    property_name: Mapped[str] = mapped_column(String(255), nullable=False)
    value_float: Mapped[float | None] = mapped_column(Float, nullable=True)
    value_str: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    value_bool: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    unit: Mapped[str | None] = mapped_column(String(50), nullable=True)
    source: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_dft_computed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    uncertainty: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    material: Mapped["Material"] = relationship(
        "Material", back_populates="properties"
    )


class MaterialStructure(Base):
    __tablename__ = "material_structures"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    material_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("materials.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    lattice_a: Mapped[float | None] = mapped_column(Float, nullable=True)
    lattice_b: Mapped[float | None] = mapped_column(Float, nullable=True)
    lattice_c: Mapped[float | None] = mapped_column(Float, nullable=True)
    alpha: Mapped[float | None] = mapped_column(Float, nullable=True)
    beta: Mapped[float | None] = mapped_column(Float, nullable=True)
    gamma: Mapped[float | None] = mapped_column(Float, nullable=True)
    volume: Mapped[float | None] = mapped_column(Float, nullable=True)
    density: Mapped[float | None] = mapped_column(Float, nullable=True)
    space_group_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    space_group_symbol: Mapped[str | None] = mapped_column(String(20), nullable=True)
    crystal_system: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # pymatgen-compatible serialised structure
    structure_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    material: Mapped["Material"] = relationship(
        "Material", back_populates="structure"
    )
