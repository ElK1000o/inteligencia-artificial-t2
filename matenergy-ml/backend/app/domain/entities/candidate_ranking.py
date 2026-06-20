from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID
from typing import Optional
from app.core.constants import CandidatePriority, ApplicationTarget


@dataclass
class RankingWeights:
    stability_weight: float = 0.30
    target_property_weight: float = 0.25
    energy_relevance_weight: float = 0.20
    abundance_weight: float = 0.10
    toxicity_penalty_weight: float = 0.05
    uncertainty_penalty_weight: float = 0.05
    out_of_domain_penalty_weight: float = 0.05

    def validate(self) -> bool:
        total = (
            self.stability_weight
            + self.target_property_weight
            + self.energy_relevance_weight
            + self.abundance_weight
            + self.toxicity_penalty_weight
            + self.uncertainty_penalty_weight
            + self.out_of_domain_penalty_weight
        )
        return abs(total - 1.0) < 1e-6


@dataclass
class CandidateRankingItem:
    material_id: UUID
    rank_position: int
    candidate_score: float  # 0.0 - 1.0
    priority_label: CandidatePriority
    reasoning_summary: str
    stability_score: Optional[float] = None
    target_property_score: Optional[float] = None
    energy_relevance_score: Optional[float] = None
    abundance_score: Optional[float] = None
    toxicity_penalty: Optional[float] = None
    uncertainty_penalty: Optional[float] = None
    out_of_domain_penalty: Optional[float] = None


@dataclass
class CandidateRanking:
    id: UUID
    name: str
    application_target: ApplicationTarget
    dataset_id: UUID
    weights: RankingWeights
    created_at: datetime
    created_by: UUID
    items: list[CandidateRankingItem] = field(default_factory=list)
    description: Optional[str] = None
    model_version_id: Optional[UUID] = None

    @property
    def n_candidates(self) -> int:
        return len(self.items)
