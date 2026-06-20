"""
Dataset Pydantic v2 schemas.
"""
from pydantic import BaseModel, ConfigDict, field_validator
from uuid import UUID
from datetime import datetime
from typing import Optional


class DatasetUploadMetadata(BaseModel):
    name: str
    description: Optional[str] = None
    source_type: str = "csv_local"
    allow_partial_import: bool = False


class DatasetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: Optional[str]
    sha256_hash: str
    row_count: Optional[int]
    valid_row_count: Optional[int]
    rejected_row_count: Optional[int]
    status: str
    available_properties: Optional[list]
    imported_at: Optional[datetime]
    imported_by: Optional[UUID]


class DatasetValidationReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    dataset_id: UUID
    total_rows: Optional[int]
    valid_rows: Optional[int]
    rejected_rows: Optional[int]
    validation_errors: Optional[dict]
    warnings: Optional[list | dict]  # stored as JSONB — can be list or dict
    validated_at: Optional[datetime]


class RejectedRowResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    row_number: Optional[int]
    raw_data: Optional[dict]
    rejection_reasons: Optional[list | dict]  # stored as JSONB
