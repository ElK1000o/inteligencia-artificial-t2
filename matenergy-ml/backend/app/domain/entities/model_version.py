from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID
from typing import Optional
from app.core.constants import ModelType, TaskType


@dataclass
class ModelMetric:
    metric_name: str
    metric_value: float
    split: str  # train, test, cv


@dataclass
class ModelVersion:
    id: UUID
    name: str
    model_type: ModelType
    task_type: TaskType
    target_property: str
    descriptor_set_id: UUID
    dataset_id: UUID
    is_active: bool
    created_at: datetime
    created_by: UUID
    version_tag: Optional[str] = None
    description: Optional[str] = None
    metrics: list[ModelMetric] = field(default_factory=list)
    hyperparameters: dict = field(default_factory=dict)
    artifact_path: Optional[str] = None
    artifact_hash: Optional[str] = None

    def get_metric(self, name: str, split: str = "test") -> Optional[float]:
        m = next(
            (m for m in self.metrics if m.metric_name == name and m.split == split),
            None,
        )
        return m.metric_value if m else None
