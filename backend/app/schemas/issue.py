from datetime import datetime
from typing import List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

IssueStatus = Literal["open", "acknowledged", "resolved", "ignored"]


class FixSuggestionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    explanation: str
    diff: str
    confidence: float
    added_to_knowledge_base: bool


class IssueListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    level: str
    service: str
    status: str
    occurrence_count: int
    first_seen: datetime
    last_seen: datetime
    commit_hash: Optional[str]
    commit_summary: Optional[str]
    confidence: Optional[float] = None


class IssueListResponse(BaseModel):
    items: List[IssueListItem]
    total: int
    limit: int
    offset: int


class IssueDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    level: str
    service: str
    status: str
    occurrence_count: int
    first_seen: datetime
    last_seen: datetime
    stack_trace: Optional[str] = None
    file_path: Optional[str]
    line_number: Optional[int]
    commit_hash: Optional[str]
    commit_author: Optional[str]
    commit_summary: Optional[str]
    fix_suggestion: Optional[FixSuggestionOut]


class IssueStatusUpdate(BaseModel):
    status: IssueStatus


class OpenPrRequest(BaseModel):
    base_branch: str = "main"


class OpenPrResponse(BaseModel):
    pr_url: str
