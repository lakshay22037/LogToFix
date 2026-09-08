from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class LogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class SourceType(str, Enum):
    FILE = "file"
    CLOUDWATCH = "cloudwatch"
    AZURE_MONITOR = "azure_monitor"


class NormalizedLogEvent(BaseModel):
    """Canonical log event shape. Every source-specific adapter (file tail,
    CloudWatch, Azure Monitor, ...) converts its raw events into this shape
    before they reach the ingestion API — downstream code never sees a
    source-specific format. See DECISIONS.md: "Canonical log schema +
    per-source adapters"."""

    timestamp: datetime
    level: LogLevel
    service: str
    message: str
    stack_trace: Optional[str] = None
    source_type: SourceType
    raw: str
    correlation_id: Optional[str] = Field(default=None)
