import logging
import os
import uuid
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

import app.env  # noqa: F401 — loads .env as a side effect
from app.logging_config import configure_logging, correlation_id_var
from app.rate_limit import enforce_rate_limit
from app.routers import errors, projects
from app.schemas.log_event import NormalizedLogEvent
from app.tasks import process_log_event

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # uvicorn installs its own log handlers during server startup, which
    # runs after this module is imported — calling configure_logging() at
    # import time gets silently overridden. This lifespan startup phase
    # runs after uvicorn's own logging setup, so this call is the one that
    # sticks.
    configure_logging()
    yield


app = FastAPI(title="Log-to-Fix", lifespan=lifespan)

# Scoped to the frontend's actual origin — never a wildcard (see
# DECISIONS.md's security review: CORS was deliberately deferred until a
# real frontend existed to scope this to).
FRONTEND_ORIGIN = os.environ.get("FRONTEND_ORIGIN", "http://localhost:5173")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_ORIGIN],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


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


app.include_router(projects.router)
app.include_router(errors.router)
