import contextvars
import json
import logging

# Set once per request (API) or once per task (worker) so every log line
# emitted while handling it carries the same id — traces a single error
# across API -> worker -> DB per ENGINEERING_STANDARDS.md's observability
# standard. Contextvars don't cross process boundaries, so the id is also
# carried explicitly on NormalizedLogEvent.correlation_id when handing off
# from the API process to the Celery worker process.
correlation_id_var = contextvars.ContextVar("correlation_id", default=None)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        correlation_id = correlation_id_var.get()
        if correlation_id:
            payload["correlation_id"] = correlation_id
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        if record.stack_info:
            payload["stack_info"] = self.formatStack(record.stack_info)
        return json.dumps(payload)


def configure_logging(level: int = logging.INFO) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    logging.basicConfig(level=level, handlers=[handler], force=True)
