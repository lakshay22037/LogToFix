from fastapi import FastAPI

import app.env  # noqa: F401 — loads .env as a side effect
from app.schemas.log_event import NormalizedLogEvent
from app.tasks import process_log_event

app = FastAPI(title="Log-to-Fix")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/logs/ingest", status_code=202)
def ingest_log(event: NormalizedLogEvent):
    process_log_event.delay(event.model_dump(mode="json"))
    return {"accepted": True}
