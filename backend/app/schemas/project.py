from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

SourceType = Literal["file", "cloudwatch", "azure_monitor"]

# Only "file" actually polls today (the file-tail adapter). The others are
# modeled and configurable so their adapters can be dropped in later
# without a schema change — see DECISIONS.md.
ACTIVE_SOURCE_TYPES = {"file"}


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)


class ProjectSettingsUpdate(BaseModel):
    webhook_url: Optional[str] = None
    github_repo: Optional[str] = None
    github_token: Optional[str] = None  # write-only; never echoed back


class ProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    created_at: datetime
    source_count: int = 0
    webhook_url: Optional[str] = None
    github_repo: Optional[str] = None
    github_connected: bool = False


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


class LogSourceCreated(LogSourceOut):
    # Only returned once, at creation time — the shipper must copy it then.
    # We don't store it anywhere retrievable in plaintext after this
    # response, matching how most API-key UXes ("copy it now, you won't
    # see it again") avoid keeping a long-lived plaintext copy in transit.
    api_key: str


class ProjectListResponse(BaseModel):
    items: List[ProjectOut]


class LogSourceListResponse(BaseModel):
    items: List[LogSourceOut]


class ProjectMemberInvite(BaseModel):
    email: str = Field(min_length=3, max_length=320)


class ProjectMemberOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    user_id: Optional[str]
    invited_at: datetime


class ProjectMemberListResponse(BaseModel):
    items: List[ProjectMemberOut]
