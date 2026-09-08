from app.adapters.file_tail_adapter import FileTailAdapter
from app.schemas.log_event import LogLevel, SourceType


def test_parses_simple_info_line():
    adapter = FileTailAdapter()
    raw = "2026-09-08 10:00:00,000 INFO [orders] Fetched order 1"

    event = adapter.parse(raw)

    assert event is not None
    assert event.level == LogLevel.INFO
    assert event.service == "orders"
    assert event.message == "Fetched order 1"
    assert event.source_type == SourceType.FILE
    assert event.stack_trace is None
    assert event.raw == raw


def test_parses_multiline_error_with_traceback():
    raw = (
        "2026-09-08 10:00:00,000 ERROR [orders] Failed to fetch order 1\n"
        "Traceback (most recent call last):\n"
        '  File "app.py", line 10, in get_order\n'
        "    raise ValueError()\n"
        "ValueError"
    )

    event = FileTailAdapter().parse(raw)

    assert event.level == LogLevel.ERROR
    assert event.message == "Failed to fetch order 1"
    assert "Traceback" in event.stack_trace
    assert "ValueError" in event.stack_trace


def test_returns_none_for_unrecognized_line():
    assert FileTailAdapter().parse("this is not a log line at all") is None


def test_returns_none_for_empty_input():
    assert FileTailAdapter().parse("") is None
