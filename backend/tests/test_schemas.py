from datetime import datetime

import pytest
from pydantic import ValidationError

from app.schemas.log_event import LogLevel, NormalizedLogEvent, SourceType


def _valid_event_kwargs(**overrides):
    kwargs = dict(
        timestamp=datetime.now(),
        level=LogLevel.ERROR,
        service="orders",
        message="something broke",
        source_type=SourceType.FILE,
        raw="raw log line",
    )
    kwargs.update(overrides)
    return kwargs


def test_valid_event_parses_successfully():
    event = NormalizedLogEvent(**_valid_event_kwargs())
    assert event.level == LogLevel.ERROR
    assert event.stack_trace is None
    assert event.correlation_id is None


def test_rejects_invalid_level():
    with pytest.raises(ValidationError):
        NormalizedLogEvent(**_valid_event_kwargs(level="NOT_A_LEVEL"))


def test_rejects_missing_required_field():
    kwargs = _valid_event_kwargs()
    del kwargs["message"]
    with pytest.raises(ValidationError):
        NormalizedLogEvent(**kwargs)


def test_rejects_invalid_source_type():
    with pytest.raises(ValidationError):
        NormalizedLogEvent(**_valid_event_kwargs(source_type="not-a-source"))
