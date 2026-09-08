import os

from celery import Celery
from celery.signals import after_setup_logger, after_setup_task_logger

import app.env  # noqa: F401 — loads .env as a side effect
from app.logging_config import JsonFormatter

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery("logtofix", broker=REDIS_URL, backend=REDIS_URL, include=["app.tasks"])
celery_app.conf.task_serializer = "json"
celery_app.conf.result_serializer = "json"
celery_app.conf.accept_content = ["json"]


# Celery installs its own log handlers during worker startup, after this
# module is imported — a plain logging.basicConfig() call here would be
# silently overridden. These signals are Celery's documented hook for
# customizing the worker's actual logging setup.
@after_setup_logger.connect
@after_setup_task_logger.connect
def _use_json_formatter(logger, *args, **kwargs):
    for handler in logger.handlers:
        handler.setFormatter(JsonFormatter())
