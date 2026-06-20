from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID
from typing import Optional
from app.core.constants import DataSource


@dataclass
class Dataset:
    id: UUID
    name: str
    sha256_hash: str
    source_type: DataSource
    row_count: int
    valid_row_count: int
    rejected_row_count: int
    column_names: list[str]
    available_properties: list[str]
    status: str  # pending, validating, valid, invalid, partial
    imported_by: UUID
    imported_at: datetime
    description: Optional[str] = None
    file_path: Optional[str] = None
    source_id: Optional[UUID] = None
    metadata: dict = field(default_factory=dict)
