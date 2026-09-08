import hashlib
import logging
import uuid

from llm_core.client import LLMSuggestionError
from llm_core.embeddings import EmbeddingError, get_default_embedder
from llm_core.fix_suggester import suggest_fix

from app.celery_app import celery_app
from app.correlation import correlate_error_to_commit, read_code_context
from app.db import SessionLocal
from app.logging_config import correlation_id_var
from app.models import FixSuggestionRecord, Issue, LogEventRecord, Project
from app.retrieval import retrieve_similar_fixes
from app.schemas.log_event import NormalizedLogEvent
from app.webhooks import notify_new_issue

logger = logging.getLogger(__name__)


@celery_app.task(name="process_log_event")
def process_log_event(event_data: dict) -> None:
    event = NormalizedLogEvent(**event_data)

    # Carries the id set by the API's request middleware (via
    # event.correlation_id) into this process, so every log line below
    # traces back to the same request — see logging_config.py.
    token = correlation_id_var.set(event.correlation_id or str(uuid.uuid4()))
    try:
        _process(event)
    finally:
        correlation_id_var.reset(token)


def _fingerprint(event: NormalizedLogEvent, correlation: dict) -> str:
    """Identifies "the same bug" across repeated occurrences. When
    correlation succeeded, the exact (commit, file, line) triple is a much
    stronger identity than the message text (which can carry
    request-specific values); fall back to the message when correlation is
    unavailable so uncorrelated errors still dedupe."""
    if correlation:
        basis = f"{correlation['commit']}:{correlation['file']}:{correlation['line']}"
    else:
        basis = f"{event.service}:{event.message}"
    return hashlib.sha256(basis.encode()).hexdigest()[:32]


def _process(event: NormalizedLogEvent) -> None:
    logger.info("Processing event: %s [%s] %s", event.level, event.service, event.message)

    if not event.stack_trace:
        return

    correlation = correlate_error_to_commit(event.stack_trace)
    if correlation is None:
        logger.warning("Could not correlate error to a commit: %s", event.message)

    fingerprint = _fingerprint(event, correlation)

    session = SessionLocal()
    try:
        existing_issue = (
            session.query(Issue)
            .filter(Issue.log_source_id == event.source_id, Issue.fingerprint == fingerprint)
            .first()
        )

        if existing_issue is not None:
            # Same bug firing again — just bump the counters and record
            # the raw occurrence. No re-correlation, no RAG lookup, no LLM
            # call: re-diagnosing an already-diagnosed bug on every
            # occurrence would be pure waste (see DECISIONS.md: load
            # testing found the LLM call is the dominant cost/latency).
            existing_issue.occurrence_count += 1
            existing_issue.last_seen = event.timestamp
            _persist_event(session, event, correlation, existing_issue.id)
            session.commit()
            return

        issue = Issue(
            log_source_id=event.source_id,
            fingerprint=fingerprint,
            title=event.message[:500],
            level=event.level.value,
            service=event.service,
            occurrence_count=1,
            first_seen=event.timestamp,
            last_seen=event.timestamp,
            commit_hash=correlation["commit"] if correlation else None,
            commit_author=correlation["author"] if correlation else None,
            commit_summary=correlation["summary"] if correlation else None,
            file_path=correlation["file"] if correlation else None,
            line_number=correlation["line"] if correlation else None,
        )
        session.add(issue)
        session.flush()  # assigns issue.id
        _persist_event(session, event, correlation, issue.id)
        session.commit()
        issue_id = issue.id
        project_id = _project_id_for_source(session, event.source_id)
    finally:
        session.close()

    if correlation is None:
        return  # nothing to diagnose without a code correlation

    _diagnose_and_notify(issue_id, project_id, event, correlation)


def _project_id_for_source(session, log_source_id):
    if log_source_id is None:
        return None
    from app.models import LogSource

    source = session.query(LogSource).filter(LogSource.id == log_source_id).first()
    return source.project_id if source else None


def _persist_event(session, event: NormalizedLogEvent, correlation, issue_id) -> None:
    session.add(LogEventRecord(
        log_source_id=event.source_id,
        issue_id=issue_id,
        timestamp=event.timestamp,
        level=event.level.value,
        service=event.service,
        message=event.message,
        stack_trace=event.stack_trace,
        source_type=event.source_type.value,
        raw=event.raw,
        correlation_id=event.correlation_id,
        commit_hash=correlation["commit"] if correlation else None,
        commit_author=correlation["author"] if correlation else None,
        commit_summary=correlation["summary"] if correlation else None,
        file_path=correlation["file"] if correlation else None,
        line_number=correlation["line"] if correlation else None,
    ))


def _diagnose_and_notify(issue_id, project_id, event: NormalizedLogEvent, correlation: dict) -> None:
    logger.info(
        "Correlated to commit %s by %s: %s (%s:%s)",
        correlation["commit"][:8],
        correlation["author"],
        correlation["summary"],
        correlation["file"],
        correlation["line"],
    )

    retrieved_examples = []
    try:
        query_embedding = get_default_embedder().embed(event.message)
        retrieved_examples = retrieve_similar_fixes(query_embedding, top_k=3)
        logger.info("Retrieved %d similar past fix(es) from the RAG corpus", len(retrieved_examples))
    except EmbeddingError:
        # RAG is an enhancement, not a hard dependency — fall back to an
        # ungrounded suggestion rather than failing the whole pipeline.
        logger.exception("Embedding/retrieval failed; continuing without RAG context")

    code_context = read_code_context(correlation["repo_root"], correlation["file"], correlation["line"])
    try:
        suggestion = suggest_fix(event.message, event.stack_trace, correlation, code_context, retrieved_examples)
    except LLMSuggestionError:
        logger.exception("Fix suggestion failed for event: %s", event.message)
        return

    logger.info("Suggested fix (confidence %.2f): %s", suggestion.confidence, suggestion.explanation)

    session = SessionLocal()
    try:
        session.add(FixSuggestionRecord(
            issue_id=issue_id,
            explanation=suggestion.explanation,
            diff=suggestion.diff,
            confidence=suggestion.confidence,
        ))
        session.commit()
    except Exception:
        session.rollback()
        logger.exception("Failed to persist fix suggestion")
    finally:
        session.close()

    if project_id is not None:
        session = SessionLocal()
        try:
            project = session.query(Project).filter(Project.id == project_id).first()
            issue = session.query(Issue).filter(Issue.id == issue_id).first()
            if project is not None and issue is not None:
                notify_new_issue(project, issue)
        finally:
            session.close()
