import logging

from app.celery_app import celery_app
from app.correlation import correlate_error_to_commit
from app.schemas.log_event import NormalizedLogEvent

logger = logging.getLogger(__name__)


@celery_app.task(name="process_log_event")
def process_log_event(event_data: dict) -> None:
    event = NormalizedLogEvent(**event_data)
    logger.info("Processing event: %s [%s] %s", event.level, event.service, event.message)

    if not event.stack_trace:
        return

    correlation = correlate_error_to_commit(event.stack_trace)
    if correlation is None:
        logger.warning("Could not correlate error to a commit: %s", event.message)
        return

    # RAG retrieval + LLM fix suggestion (next steps) will consume this
    # correlation result — logged for now since there's no storage layer yet.
    logger.info(
        "Correlated to commit %s by %s: %s (%s:%s)",
        correlation["commit"][:8],
        correlation["author"],
        correlation["summary"],
        correlation["file"],
        correlation["line"],
    )
