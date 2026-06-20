"""
Common Pydantic v2 schemas shared across the application.
"""
from pydantic import BaseModel, ConfigDict
from datetime import datetime
from uuid import UUID


class TimestampMixin(BaseModel):
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class PaginatedResponse(BaseModel):
    total: int
    skip: int
    limit: int
    items: list


class MessageResponse(BaseModel):
    message: str


class ErrorResponse(BaseModel):
    error: str
    message: str
    recommended_action: str = ""
