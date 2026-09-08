from datetime import datetime

import pytest
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from app.db import SessionLocal, engine
from app.models import FixSuggestionRecord, LogEventRecord
from app.schemas.log_event import LogLevel, NormalizedLogEvent, SourceType
from app.tasks import _persist
from llm_core.schemas import FixSuggestion


def _postgres_reachable() -> bool:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except OperationalError:
        return False


requires_postgres = pytest.mark.skipif(
    not _postgres_reachable(), reason="Postgres not reachable at DATABASE_URL"
)


@requires_postgres
def test_persist_writes_log_event_and_fix_suggestion():
    event = NormalizedLogEvent(
        timestamp=datetime.now(),
        level=LogLevel.ERROR,
        service="test-service",
        message="a test error for the persistence test",
        stack_trace="Traceback...\nValueError: test",
        source_type=SourceType.FILE,
        raw="raw log line for test",
    )
    correlation = {
        "commit": "deadbeef" * 5,
        "author": "Test Author",
        "summary": "Test commit summary",
        "file": "app.py",
        "line": 1,
    }
    suggestion = FixSuggestion(explanation="test explanation", diff="- old\n+ new", confidence=0.5)

    _persist(event, correlation, suggestion)

    session = SessionLocal()
    try:
        log_event_row = (
            session.query(LogEventRecord)
            .filter(LogEventRecord.message == event.message)
            .order_by(LogEventRecord.created_at.desc())
            .first()
        )
        assert log_event_row is not None
        assert log_event_row.commit_hash == correlation["commit"]

        fix_row = (
            session.query(FixSuggestionRecord)
            .filter(FixSuggestionRecord.log_event_id == log_event_row.id)
            .first()
        )
        assert fix_row is not None
        assert fix_row.confidence == 0.5
        assert fix_row.explanation == "test explanation"
    finally:
        # keep the test idempotent / not littering the DB across runs
        if log_event_row is not None:
            session.query(FixSuggestionRecord).filter(
                FixSuggestionRecord.log_event_id == log_event_row.id
            ).delete()
            session.query(LogEventRecord).filter(LogEventRecord.id == log_event_row.id).delete()
            session.commit()
        session.close()


@requires_postgres
def test_persist_without_suggestion_still_writes_log_event():
    event = NormalizedLogEvent(
        timestamp=datetime.now(),
        level=LogLevel.ERROR,
        service="test-service",
        message="an error with no fix suggestion (LLM failed)",
        stack_trace="Traceback...\nValueError: test",
        source_type=SourceType.FILE,
        raw="raw log line",
    )
    correlation = {
        "commit": "cafebabe" * 5,
        "author": "Test Author",
        "summary": "Test commit summary",
        "file": "app.py",
        "line": 1,
    }

    _persist(event, correlation, suggestion=None)

    session = SessionLocal()
    try:
        log_event_row = (
            session.query(LogEventRecord)
            .filter(LogEventRecord.message == event.message)
            .order_by(LogEventRecord.created_at.desc())
            .first()
        )
        assert log_event_row is not None

        fix_row = (
            session.query(FixSuggestionRecord)
            .filter(FixSuggestionRecord.log_event_id == log_event_row.id)
            .first()
        )
        assert fix_row is None
    finally:
        if log_event_row is not None:
            session.query(LogEventRecord).filter(LogEventRecord.id == log_event_row.id).delete()
            session.commit()
        session.close()
