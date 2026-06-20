from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID
from typing import Optional
import numpy as np


@dataclass
class DescriptorSet:
    id: UUID
    name: str
    version: str
    descriptor_type: str  # compositional, structural, combined
    library_versions: dict
    feature_names: list[str]
    n_features: int
    created_at: datetime
    created_by: UUID


@dataclass
class DescriptorVector:
    material_id: UUID
    descriptor_set_id: UUID
    vector: list[float]
    computed_at: datetime
    has_nan: bool = False
    nan_features: list[str] = field(default_factory=list)

    def to_numpy(self) -> np.ndarray:
        return np.array(self.vector, dtype=np.float64)
