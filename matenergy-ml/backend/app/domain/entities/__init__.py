"""
Domain entities for MatEnergy-ML.

All pure-Python dataclasses — no I/O, no ORM, no framework dependencies.
"""
from app.domain.entities.material import (
    Material,
    MaterialCompositionItem,
    MaterialProperty,
)
from app.domain.entities.dataset import Dataset
from app.domain.entities.model_version import ModelMetric, ModelVersion
from app.domain.entities.prediction import Prediction
from app.domain.entities.candidate_ranking import (
    CandidateRanking,
    CandidateRankingItem,
    RankingWeights,
)
from app.domain.entities.descriptor import DescriptorSet, DescriptorVector
from app.domain.entities.user import User

__all__ = [
    # material
    "Material",
    "MaterialCompositionItem",
    "MaterialProperty",
    # dataset
    "Dataset",
    # model
    "ModelMetric",
    "ModelVersion",
    # prediction
    "Prediction",
    # ranking
    "CandidateRanking",
    "CandidateRankingItem",
    "RankingWeights",
    # descriptor
    "DescriptorSet",
    "DescriptorVector",
    # user
    "User",
]
