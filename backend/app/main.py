from fastapi import FastAPI

from app.schemas.log_event import NormalizedLogEvent

app = FastAPI(title="Log-to-Fix")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/logs/ingest", status_code=202)
def ingest_log(event: NormalizedLogEvent):
    # Walking-skeleton stub (see DECISIONS.md: "Project execution flow").
    # Next step in Phase 1 is pushing this to a Celery task instead of
    # handling it inline, per the scalability standard.
    print(f"received event: {event.level} [{event.service}] {event.message}")
    return {"accepted": True}
