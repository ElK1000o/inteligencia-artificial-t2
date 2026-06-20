"""
Material Pydantic v2 schemas.
"""
from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime
from typing import Optional


class MaterialResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    formula: str
    reduced_formula: Optional[str]
    chemsys: Optional[str]
    nelements: Optional[int]
    elements: Optional[list]
    dataset_id: Optional[UUID]
    created_at: Optional[datetime]


class MaterialPropertyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    property_name: str
    value_float: Optional[float]
    value_str: Optional[str]
    unit: Optional[str]
    is_dft_computed: bool


class MaterialDetailResponse(MaterialResponse):
    properties: list[MaterialPropertyResponse] = []


class MaterialSearchRequest(BaseModel):
    formula_query: Optional[str] = None
    elements: Optional[list[str]] = None
    chemsys: Optional[str] = None
    dataset_id: Optional[UUID] = None
    skip: int = 0
    limit: int = 50
