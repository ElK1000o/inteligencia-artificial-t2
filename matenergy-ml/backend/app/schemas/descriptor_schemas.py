"""
Descriptor Pydantic v2 schemas.
"""
from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime
from typing import Optional


class GenerateDescriptorsRequest(BaseModel):
    dataset_id: UUID
    include_structural: bool = False
    name: Optional[str] = None


class DescriptorSetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    version: str
    descriptor_type: Optional[str]
    n_features: Optional[int]
    created_at: datetime


class DescriptorGenerationResult(BaseModel):
    descriptor_set_id: UUID
    n_success: int
    n_error: int
    errors: list[dict] = []
    feature_names: list[str] = []
