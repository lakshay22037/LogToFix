from abc import ABC, abstractmethod
from typing import Optional

from app.schemas.log_event import NormalizedLogEvent


class LogSourceAdapter(ABC):
    """One adapter per log source (file tail, CloudWatch, Azure Monitor, ...).
    Each implementation isolates its source's raw format entirely — nothing
    downstream of `parse` ever sees a source-specific shape. See
    DECISIONS.md: "Canonical log schema + per-source adapters"."""

    source_type: str

    @abstractmethod
    def parse(self, raw_event: str) -> Optional[NormalizedLogEvent]:
        """Convert one raw event from this source into the canonical schema.
        Returns None if the raw event doesn't match a recognizable log line
        (e.g. a stack-trace continuation line already folded into a prior
        event)."""
        raise NotImplementedError
