"""
ML model Pydantic v2 schemas.
"""
from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime
from typing import Optional


class TrainModelRequest(BaseModel):
    model_type: str
    task_type: str
    target_property: str
    dataset_id: UUID
    descriptor_set_id: UUID
    hyperparameters: Optional[dict] = None
    test_size: float = 0.2
    name: Optional[str] = None
    description: Optional[str] = None


class ModelVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    model_type: str
    task_type: Optional[str]
    target_property: str
    is_active: bool
    version_tag: Optional[str]
    created_at: datetime


class ModelMetricResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    split: str
    metric_name: str
    metric_value: float


class ModelTrainingRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: str
    n_train_samples: Optional[int]
    n_test_samples: Optional[int]
    n_features: Optional[int]
    duration_seconds: Optional[float]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]


class ModelEvaluationResponse(BaseModel):
    model_version_id: UUID
    metrics: list[ModelMetricResponse]
    feature_importances: list[dict] = []
