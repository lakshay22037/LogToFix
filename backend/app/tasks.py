import logging

from app.celery_app import celery_app
from app.schemas.log_event import NormalizedLogEvent

logger = logging.getLogger(__name__)


@celery_app.task(name="process_log_event")
def process_log_event(event_data: dict) -> None:
    event = NormalizedLogEvent(**event_data)
    # Git-blame correlation against data/demo-repo is the next step here —
    # this stub proves the queue wiring before that logic is added.
    logger.info("Processing event: %s [%s] %s", event.level, event.service, event.message)
