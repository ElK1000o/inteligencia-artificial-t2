"""
Prediction Pydantic v2 schemas.
"""
from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime
from typing import Optional


class PredictionRequest(BaseModel):
    model_version_id: UUID  # required — for the async pending-batch endpoint
    dataset_id: UUID
    material_ids: Optional[list[UUID]] = None  # None = all materials in dataset


class BatchPredictionRequest(BaseModel):
    """Frontend-facing schema for the /predictions/batch endpoint."""
    target_property: str
    dataset_id: UUID
    material_ids: list[UUID]
    model_version_id: Optional[UUID] = None


class PredictionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    material_id: UUID
    predicted_value: Optional[float]
    predicted_class: Optional[str]
    confidence_score: Optional[float]
    is_out_of_domain: bool
    out_of_domain_reason: Optional[str]
    created_at: datetime


class PredictionBatchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: str
    n_materials: Optional[int]
    created_at: datetime
    completed_at: Optional[datetime]
