from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class FixSuggestionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    explanation: str
    diff: str
    confidence: float


class ErrorListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    timestamp: datetime
    level: str
    service: str
    message: str
    commit_hash: Optional[str]
    commit_summary: Optional[str]
    confidence: Optional[float]


class ErrorListResponse(BaseModel):
    items: List[ErrorListItem]
    total: int
    limit: int
    offset: int


class ErrorDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    timestamp: datetime
    level: str
    service: str
    message: str
    stack_trace: Optional[str]
    file_path: Optional[str]
    line_number: Optional[int]
    commit_hash: Optional[str]
    commit_author: Optional[str]
    commit_summary: Optional[str]
    fix_suggestion: Optional[FixSuggestionOut]
