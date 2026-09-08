import re
from datetime import datetime
from typing import Optional

from app.adapters.base import LogSourceAdapter
from app.schemas.log_event import LogLevel, NormalizedLogEvent, SourceType

LINE_PATTERN = re.compile(
    r"^(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) "
    r"(?P<level>\w+) \[(?P<service>[\w.]+)\] (?P<message>.*)$"
)


class FileTailAdapter(LogSourceAdapter):
    """Parses the demo app's plain-text log format (see
    data/demo-repo/README.md for a sample line) into the canonical schema.
    A raw_event may span multiple lines: the first line is the log record
    itself, any following lines are an attached Python traceback."""

    source_type = SourceType.FILE

    def parse(self, raw_event: str) -> Optional[NormalizedLogEvent]:
        lines = raw_event.splitlines()
        if not lines:
            return None

        match = LINE_PATTERN.match(lines[0])
        if not match:
            return None

        stack_trace = "\n".join(lines[1:]) if len(lines) > 1 else None

        return NormalizedLogEvent(
            timestamp=datetime.strptime(match.group("timestamp"), "%Y-%m-%d %H:%M:%S,%f"),
            level=LogLevel(match.group("level")),
            service=match.group("service"),
            message=match.group("message"),
            stack_trace=stack_trace,
            source_type=self.source_type,
            raw=raw_event,
        )
