import time
from typing import Optional

import requests

from app.adapters.base import LogSourceAdapter
from app.adapters.file_tail_adapter import LINE_PATTERN, FileTailAdapter

INGEST_URL = "http://localhost:8000/logs/ingest"
POLL_INTERVAL_SECONDS = 1.0


def tail_and_ship(
    file_path: str,
    adapter: LogSourceAdapter,
    ingest_url: str = INGEST_URL,
    source_id: Optional[str] = None,
    api_key: Optional[str] = None,
) -> None:
    """Watches a log file for new lines and forwards each parsed event to the
    ingestion API — the standalone "log shipper" role described in
    DECISIONS.md, decoupled from both the app producing logs and the API
    consuming them. source_id ties every shipped event to a LogSource
    record so it shows up under the right project; api_key is the
    plaintext key shown once when that source was created (see
    models.py: LogSource.api_key_hash) — required since /logs/ingest now
    rejects unauthenticated events."""
    buffer: list[str] = []
    headers = {"X-API-Key": api_key} if api_key else {}

    def flush():
        if not buffer:
            return
        event = adapter.parse("\n".join(buffer))
        buffer.clear()
        if event is None:
            return
        payload = event.model_dump(mode="json")
        if source_id:
            payload["source_id"] = source_id
        try:
            requests.post(ingest_url, json=payload, headers=headers, timeout=5)
        except requests.exceptions.RequestException as exc:
            print(f"Failed to ship event to {ingest_url}: {exc}")

    with open(file_path, "r") as f:
        f.seek(0, 2)  # start at end of file — only ship new lines
        while True:
            line = f.readline()
            if not line:
                flush()
                time.sleep(POLL_INTERVAL_SECONDS)
                continue

            line = line.rstrip("\n")
            if LINE_PATTERN.match(line):
                flush()
                buffer.append(line)
            elif buffer:
                buffer.append(line)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("log_file", nargs="?", default="../data/demo-repo/logs/app.log")
    parser.add_argument("--source-id", default=None, help="LogSource id to tag shipped events with")
    parser.add_argument("--api-key", default=None, help="LogSource API key, shown once at creation")
    parser.add_argument("--ingest-url", default=INGEST_URL)
    args = parser.parse_args()

    tail_and_ship(
        args.log_file,
        FileTailAdapter(),
        ingest_url=args.ingest_url,
        source_id=args.source_id,
        api_key=args.api_key,
    )
