import logging
import uuid

from fastapi import Depends, FastAPI, Request

import app.env  # noqa: F401 — loads .env as a side effect
from app.logging_config import configure_logging, correlation_id_var
from app.rate_limit import enforce_rate_limit
from app.schemas.log_event import NormalizedLogEvent
from app.tasks import process_log_event

logger = logging.getLogger(__name__)

app = FastAPI(title="Log-to-Fix")


@app.on_event("startup")
async def _configure_logging():
    # uvicorn installs its own log handlers during server startup, which
    # runs after this module is imported — calling configure_logging() at
    # import time gets silently overridden. The startup event fires after
    # uvicorn's own logging setup, so this call is the one that sticks.
    configure_logging()


@app.middleware("http")
async def add_correlation_id(request: Request, call_next):
    correlation_id = request.headers.get("x-request-id") or str(uuid.uuid4())
    token = correlation_id_var.set(correlation_id)
    try:
        response = await call_next(request)
    finally:
        correlation_id_var.reset(token)
    response.headers["X-Request-ID"] = correlation_id
    return response


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/logs/ingest", status_code=202, dependencies=[Depends(enforce_rate_limit)])
def ingest_log(event: NormalizedLogEvent):
    if event.correlation_id is None:
        event.correlation_id = correlation_id_var.get()
    logger.info("Ingested event: %s [%s] %s", event.level, event.service, event.message)
    process_log_event.delay(event.model_dump(mode="json"))
    return {"accepted": True}
