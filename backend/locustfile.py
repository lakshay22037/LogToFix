"""Load test for POST /logs/ingest.

Usage:
    locust -f locustfile.py --host=http://localhost:8000 --headless \
        --users 50 --spawn-rate 10 --run-time 30s --csv=results

See DECISIONS.md: "Load testing — real bottleneck found" for what this
surfaced (the API's own ingestion throughput vs. Celery worker throughput
bottlenecked by external LLM API latency).
"""
import os
import random
from datetime import datetime, timezone

from locust import HttpUser, between, task

# Must be a real, committed line in the demo repo so correlation (git
# blame) actually succeeds — an event with no stack trace, or one pointing
# to a made-up line, exits process_log_event early and never exercises
# correlation/RAG/LLM at all. This is the exact line seeded by bug #1
# (SQL injection) — see data/demo-repo/app.py.
DEMO_REPO_PATH = os.environ.get(
    "LOCUST_DEMO_REPO_PATH", "/Users/lakshaywadhwa/Desktop/LogToFix/data/demo-repo/app.py"
)
STACK_TRACE = (
    "Traceback (most recent call last):\n"
    f'  File "{DEMO_REPO_PATH}", line 62, in get_order\n'
    "    row = conn.execute(query).fetchone()\n"
    "sqlite3.OperationalError: unrecognized token"
)


class IngestUser(HttpUser):
    wait_time = between(0.01, 0.1)

    @task
    def ingest_error(self):
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": "ERROR",
            "service": "orders",
            "message": f"Load test error {random.randint(1, 1_000_000)}",
            "stack_trace": STACK_TRACE,
            "source_type": "file",
            "raw": "raw log line for load test",
        }
        self.client.post("/logs/ingest", json=payload)
