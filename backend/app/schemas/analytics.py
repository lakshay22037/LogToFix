from typing import List, Optional

from pydantic import BaseModel


class DailyCount(BaseModel):
    date: str
    count: int


class ServiceCount(BaseModel):
    service: str
    count: int


class ProjectAnalytics(BaseModel):
    total_issues: int
    open_issues: int
    resolved_issues: int
    total_occurrences: int
    avg_confidence: Optional[float]
    issues_per_day: List[DailyCount]
    top_services: List[ServiceCount]
    avg_resolution_hours: Optional[float]
