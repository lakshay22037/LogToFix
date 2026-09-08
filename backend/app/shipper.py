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
) -> None:
    """Watches a log file for new lines and forwards each parsed event to the
    ingestion API — the standalone "log shipper" role described in
    DECISIONS.md, decoupled from both the app producing logs and the API
    consuming them. source_id ties every shipped event to a LogSource
    record so it shows up under the right project."""
    buffer: list[str] = []

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
            requests.post(ingest_url, json=payload, timeout=5)
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
    parser.add_argument("--ingest-url", default=INGEST_URL)
    args = parser.parse_args()

    tail_and_ship(args.log_file, FileTailAdapter(), ingest_url=args.ingest_url, source_id=args.source_id)
