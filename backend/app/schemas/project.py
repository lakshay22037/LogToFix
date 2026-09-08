from datetime import datetime
from typing import Any, Dict, List, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

SourceType = Literal["file", "cloudwatch", "azure_monitor"]

# Only "file" actually polls today (the file-tail adapter). The others are
# modeled and configurable so their adapters can be dropped in later
# without a schema change — see DECISIONS.md.
ACTIVE_SOURCE_TYPES = {"file"}


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)


class ProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    created_at: datetime
    source_count: int = 0


class LogSourceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    source_type: SourceType
    config: Dict[str, Any] = Field(default_factory=dict)


class LogSourceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    source_type: SourceType
    config: Dict[str, Any]
    status: str
    created_at: datetime


class ProjectListResponse(BaseModel):
    items: List[ProjectOut]


class LogSourceListResponse(BaseModel):
    items: List[LogSourceOut]
