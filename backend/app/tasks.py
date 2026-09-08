import logging

from llm_core.client import LLMSuggestionError
from llm_core.fix_suggester import suggest_fix

from app.celery_app import celery_app
from app.correlation import correlate_error_to_commit, read_code_context
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

    logger.info(
        "Correlated to commit %s by %s: %s (%s:%s)",
        correlation["commit"][:8],
        correlation["author"],
        correlation["summary"],
        correlation["file"],
        correlation["line"],
    )

    # Storage of results and RAG retrieval (next steps) are not wired in yet
    # — this proves the correlation -> LLM leg of the pipeline in isolation.
    code_context = read_code_context(correlation["repo_root"], correlation["file"], correlation["line"])
    try:
        suggestion = suggest_fix(event.message, event.stack_trace, correlation, code_context)
    except LLMSuggestionError:
        logger.exception("Fix suggestion failed for event: %s", event.message)
        return

    logger.info(
        "Suggested fix (confidence %.2f): %s",
        suggestion.confidence, suggestion.explanation,
    )
