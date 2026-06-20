"""
Candidate ranking models for material discovery workflows.

Tables: candidate_rankings, candidate_ranking_items
"""
import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
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


class CandidateRanking(Base):
    __tablename__ = "candidate_rankings"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    application_target: Mapped[str] = mapped_column(String(255), nullable=False)
    dataset_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("datasets.id", ondelete="SET NULL"),
        nullable=True,
    )
    model_version_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("model_versions.id", ondelete="SET NULL"),
        nullable=True,
    )
    # JSONB map with keys w1..w7 (scoring weights)
    weights: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    n_candidates: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    dataset: Mapped["Dataset | None"] = relationship(  # type: ignore[name-defined]
        "Dataset", foreign_keys=[dataset_id]
    )
    model_version: Mapped["ModelVersion | None"] = relationship(  # type: ignore[name-defined]
        "ModelVersion", foreign_keys=[model_version_id]
    )
    creator: Mapped["User | None"] = relationship(  # type: ignore[name-defined]
        "User", foreign_keys=[created_by]
    )
    items: Mapped[list["CandidateRankingItem"]] = relationship(
        "CandidateRankingItem", back_populates="ranking", cascade="all, delete-orphan"
    )


class CandidateRankingItem(Base):
    __tablename__ = "candidate_ranking_items"
    __table_args__ = (
        UniqueConstraint(
            "ranking_id", "material_id",
            name="uq_candidate_ranking_items_ranking_material",
        ),
        UniqueConstraint(
            "ranking_id", "rank_position",
            name="uq_candidate_ranking_items_ranking_position",
        ),
        CheckConstraint(
            "candidate_score >= 0 AND candidate_score <= 1",
            name="ck_candidate_ranking_items_score_range",
        ),
        Index("ix_candidate_ranking_items_ranking_id", "ranking_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    ranking_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("candidate_rankings.id", ondelete="CASCADE"),
        nullable=False,
    )
    material_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("materials.id", ondelete="CASCADE"),
        nullable=False,
    )
    rank_position: Mapped[int] = mapped_column(Integer, nullable=False)
    candidate_score: Mapped[float] = mapped_column(Float, nullable=False)
    # high_priority | medium_priority | low_priority | not_recommended
    priority_label: Mapped[str] = mapped_column(String(50), nullable=False)
    stability_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    target_property_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    energy_relevance_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    abundance_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    toxicity_penalty: Mapped[float | None] = mapped_column(Float, nullable=True)
    uncertainty_penalty: Mapped[float | None] = mapped_column(Float, nullable=True)
    out_of_domain_penalty: Mapped[float | None] = mapped_column(Float, nullable=True)
    reasoning_summary: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    ranking: Mapped["CandidateRanking"] = relationship(
        "CandidateRanking", back_populates="items"
    )
    material: Mapped["Material"] = relationship(  # type: ignore[name-defined]
        "Material", foreign_keys=[material_id]
    )
