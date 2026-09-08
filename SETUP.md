# Running Log-to-Fix locally

Current state: walking-skeleton (Phase 1) — demo app → file-tail shipper →
FastAPI ingestion → Celery/Redis queue → git-blame correlation → LLM fix
suggestion. Postgres, RAG, and the frontend land in later phases. This
covers running what exists today on any machine with Python 3.9+ and Docker.

You'll run five processes, each in its own terminal, in this order.

## 1. Prerequisites

- Python 3.9 or newer (`python3 --version`)
- `pip`
- Docker (for Redis) — or a local Redis install if you'd rather not use Docker
- An Anthropic API key (get one at console.anthropic.com) — copy
  `.env.example` to `.env` in `backend/` and set `ANTHROPIC_API_KEY`, or
  export it in Terminal 3's shell before starting the backend/worker.
  Without it, correlation and everything else still works — only the final
  fix-suggestion step fails (logged, doesn't crash the worker).

## 2. Terminal 1 — Redis (the Celery broker)

```bash
docker compose up redis
```

Leave this running. (No Docker? Install Redis locally and run
`redis-server` instead — same effect.)

## 3. Terminal 2 — the demo app (the "live" error source)

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

## 4. Terminal 3 — the backend (ingestion API)

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

## 5. Terminal 4 — the Celery worker (processes ingested events)

```bash
cd backend
source .venv/bin/activate   # same venv as step 4 (macOS/Linux); Windows: .venv\Scripts\Activate.ps1

python3 -m celery -A app.celery_app worker --loglevel=info
```

Picks up tasks enqueued by the ingestion API and processes them (currently a
logging stub — git-blame correlation is the next piece to land here). Leave
this running.

## 6. Terminal 5 — the log shipper (tails the demo app's logs, forwards to ingestion)

```bash
cd backend
source .venv/bin/activate   # same venv as step 4 (macOS/Linux); Windows: .venv\Scripts\Activate.ps1

python3 -m app.shipper ../data/demo-repo/logs/app.log
```

This process watches the log file and POSTs each new parsed event to
`http://localhost:8000/logs/ingest`. Leave this running.

## 7. Generate traffic

In a sixth terminal, hit the demo app's endpoints manually, or generate
continuous traffic (including triggering the seeded bugs) automatically:

```bash
cd data/demo-repo
source .venv/bin/activate    # Windows: .venv\Scripts\Activate.ps1
python traffic_generator.py
```

## 8. What to expect

- Terminal 2 (demo app) logs each request, including full tracebacks for the
  5 seeded bugs (see `data/demo-repo/README.md` for what they are).
- Terminal 6 (shipper) picks up new log lines as they're written.
- Terminal 3 (backend) returns `202 Accepted` immediately for each ingested
  event — it doesn't wait for processing.
- Terminal 4 (Celery worker) logs `Processing event: ...` for each task it
  picks up from the queue.

## Stopping everything

`Ctrl+C` in each terminal (and `docker compose down` for Redis). Runtime
artifacts (`.venv/`, `logs/app.log`, `demo.db`) are gitignored and safe to
delete between runs if you want a clean slate:

```bash
rm -rf backend/.venv data/demo-repo/.venv data/demo-repo/demo.db data/demo-repo/logs/app.log*
```

---

This file will be updated as later phases add Postgres, the RAG pipeline,
and the frontend — at that point `docker compose up` will replace most of
the manual steps above.
