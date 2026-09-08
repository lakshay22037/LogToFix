from pathlib import Path

from dotenv import load_dotenv

# Imported (for its side effect) by every standalone entry point — the
# FastAPI app, the Celery worker, and one-off scripts — so .env is loaded
# exactly once, in one place, before any of them read an env var.
load_dotenv(Path(__file__).resolve().parents[2] / ".env")
