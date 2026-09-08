# Running Log-to-Fix locally

Current state: walking-skeleton (Phase 1) — demo app → file-tail shipper →
FastAPI ingestion stub. No Docker Compose, Postgres, Redis, or frontend yet
(those land in later phases). This covers running what exists today on any
machine with Python 3.9+.

You'll run three processes, each in its own terminal, in this order.

## 1. Prerequisites

- Python 3.9 or newer (`python3 --version`)
- `pip`

## 2. Terminal 1 — the demo app (the "live" error source)

```bash
cd data/demo-repo
python3 -m venv .venv

# macOS / Linux
source .venv/bin/activate
# Windows (PowerShell)
.venv\Scripts\Activate.ps1

pip install -r requirements.txt
python app.py
```

Runs on `http://localhost:5001`. Writes logs to `data/demo-repo/logs/app.log`.
Leave this running.

## 3. Terminal 2 — the backend (ingestion API)

```bash
cd backend
python3 -m venv .venv

# macOS / Linux
source .venv/bin/activate
# Windows (PowerShell)
.venv\Scripts\Activate.ps1

pip install -r requirements.txt
python3 -m uvicorn app.main:app --port 8000
```

Runs on `http://localhost:8000`. Visit `http://localhost:8000/docs` for the
interactive API docs. Leave this running.

## 4. Terminal 3 — the log shipper (tails the demo app's logs, forwards to ingestion)

```bash
cd backend
source .venv/bin/activate   # same venv as step 3 (macOS/Linux); Windows: .venv\Scripts\Activate.ps1

python3 -m app.shipper ../data/demo-repo/logs/app.log
```

This process watches the log file and POSTs each new parsed event to
`http://localhost:8000/logs/ingest`. Leave this running.

## 5. Generate traffic

In a fourth terminal, hit the demo app's endpoints manually, or generate
continuous traffic (including triggering the seeded bugs) automatically:

```bash
cd data/demo-repo
source .venv/bin/activate    # Windows: .venv\Scripts\Activate.ps1
python traffic_generator.py
```

## 6. What to expect

- Terminal 1 (demo app) logs each request, including full tracebacks for the
  5 seeded bugs (see `data/demo-repo/README.md` for what they are).
- Terminal 3 (shipper) picks up new log lines as they're written.
- Terminal 2 (backend) prints `received event: ...` for each event it
  ingests, and returns `202 Accepted`.

## Stopping everything

`Ctrl+C` in each terminal. Runtime artifacts (`.venv/`, `logs/app.log`,
`demo.db`) are gitignored and safe to delete between runs if you want a clean
slate:

```bash
rm -rf backend/.venv data/demo-repo/.venv data/demo-repo/demo.db data/demo-repo/logs/app.log*
```

---

This file will be updated as later phases add Docker Compose, Postgres,
Redis/Celery, the RAG pipeline, and the frontend — at that point `docker
compose up` will replace most of the manual steps above.
