from dataclasses import dataclass
from datetime import datetime
from uuid import UUID
from typing import Optional


@dataclass
class Prediction:
    id: UUID
    batch_id: UUID
    material_id: UUID
    created_at: datetime
    predicted_value: Optional[float] = None
    predicted_class: Optional[str] = None
    confidence_score: Optional[float] = None
    is_out_of_domain: bool = False
    out_of_domain_reason: Optional[str] = None
    is_calibrated: bool = False
