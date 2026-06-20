"""
Candidate ranking Pydantic v2 schemas.
"""
from pydantic import BaseModel, ConfigDict, field_validator
from uuid import UUID
from datetime import datetime
from typing import Optional


class RankingWeightsSchema(BaseModel):
    stability_weight: float = 0.30
    target_property_weight: float = 0.25
    energy_relevance_weight: float = 0.20
    abundance_weight: float = 0.10
    toxicity_penalty_weight: float = 0.05
    uncertainty_penalty_weight: float = 0.05
    out_of_domain_penalty_weight: float = 0.05

    @field_validator(
        "stability_weight",
        "target_property_weight",
        "energy_relevance_weight",
        "abundance_weight",
        "toxicity_penalty_weight",
        "uncertainty_penalty_weight",
        "out_of_domain_penalty_weight",
    )
    @classmethod
    def weight_range(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError("Each weight must be between 0 and 1")
        return v


class CreateRankingRequest(BaseModel):
    name: str
    application_target: str
    dataset_id: UUID
    model_version_id: Optional[UUID] = None
    weights: RankingWeightsSchema = RankingWeightsSchema()
    description: Optional[str] = None


class RankingItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    material_id: UUID
    rank_position: int
    candidate_score: float
    priority_label: str
    reasoning_summary: str
    stability_score: Optional[float]
    uncertainty_penalty: Optional[float]
    is_out_of_domain: bool = False


class CandidateRankingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    application_target: str
    n_candidates: Optional[int]
    created_at: datetime


class CandidateRankingDetailResponse(CandidateRankingResponse):
    items: list[RankingItemResponse] = []
    weights: dict = {}
