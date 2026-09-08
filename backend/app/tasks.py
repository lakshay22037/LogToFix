import logging
import uuid

from llm_core.client import LLMSuggestionError
from llm_core.embeddings import EmbeddingError, get_default_embedder
from llm_core.fix_suggester import suggest_fix

from app.celery_app import celery_app
from app.correlation import correlate_error_to_commit, read_code_context
from app.db import SessionLocal
from app.logging_config import correlation_id_var
from app.models import FixSuggestionRecord, LogEventRecord
from app.retrieval import retrieve_similar_fixes
from app.schemas.log_event import NormalizedLogEvent

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


def _process(event: NormalizedLogEvent) -> None:
    logger.info("Processing event: %s [%s] %s", event.level, event.service, event.message)

    if not event.stack_trace:
        return

    correlation = correlate_error_to_commit(event.stack_trace)
    if correlation is None:
        logger.warning("Could not correlate error to a commit: %s", event.message)
        return

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
        _persist(event, correlation, suggestion=None)
        return

    logger.info(
        "Suggested fix (confidence %.2f): %s",
        suggestion.confidence, suggestion.explanation,
    )
    _persist(event, correlation, suggestion)


def _persist(event: NormalizedLogEvent, correlation: dict, suggestion) -> None:
    session = SessionLocal()
    try:
        log_event_record = LogEventRecord(
            log_source_id=event.source_id,
            timestamp=event.timestamp,
            level=event.level.value,
            service=event.service,
            message=event.message,
            stack_trace=event.stack_trace,
            source_type=event.source_type.value,
            raw=event.raw,
            correlation_id=event.correlation_id,
            commit_hash=correlation["commit"],
            commit_author=correlation["author"],
            commit_summary=correlation["summary"],
            file_path=correlation["file"],
            line_number=correlation["line"],
        )
        session.add(log_event_record)
        session.flush()  # assigns log_event_record.id

        if suggestion is not None:
            session.add(FixSuggestionRecord(
                log_event_id=log_event_record.id,
                explanation=suggestion.explanation,
                diff=suggestion.diff,
                confidence=suggestion.confidence,
            ))

        session.commit()
    except Exception:
        session.rollback()
        logger.exception("Failed to persist log event / fix suggestion")
    finally:
        session.close()
