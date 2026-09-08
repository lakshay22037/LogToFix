import os
from pathlib import Path

from celery import Celery
from dotenv import load_dotenv

# Loaded here since this module is imported by both process entry points
# (uvicorn via app.main -> app.tasks, and the Celery worker itself) before
# any env var (REDIS_URL, ANTHROPIC_API_KEY, ...) is read.
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery("logtofix", broker=REDIS_URL, backend=REDIS_URL, include=["app.tasks"])
celery_app.conf.task_serializer = "json"
celery_app.conf.result_serializer = "json"
celery_app.conf.accept_content = ["json"]
