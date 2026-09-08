# Engineering Standards — Log-to-Fix

This file is the bar every piece of code in this repo is written against. Read it
before writing code in a given area; it's not a wishlist, it's a checklist. When a
tradeoff is made against one of these standards (e.g. skipping a retry policy for
now), it must be logged in [DECISIONS.md](DECISIONS.md) with why.

---

## 1. Frontend — must be genuinely responsive

- Mobile-first CSS: design for smallest viewport first, scale up with
  breakpoints (Tailwind's `sm/md/lg/xl` or equivalent) — never desktop-first
  with mobile as an afterthought.
- No fixed pixel widths on layout containers; use flex/grid with relative
  units (`%`, `rem`, `fr`, `minmax()`).
- Test every screen at minimum: 375px (mobile), 768px (tablet), 1440px
  (desktop) before considering a component done.
- Tables/diff-viewers that overflow on small screens must scroll horizontally
  within their own container, never break the page layout.
- Loading, empty, and error states are required for every data-fetching
  component — never ship a component that only handles the happy path.
- Accessibility baseline: semantic HTML, sufficient color contrast, keyboard
  navigable interactive elements, `alt` text on meaningful images.
- No layout-shift on data load — reserve space (skeletons) rather than
  popping content in.

## 2. Backend — must be scalable by design

- Every endpoint that does non-trivial work (git ops, embeddings, LLM calls)
  is async and offloads real work to a Celery task — nothing slow blocks the
  event loop or the request/response cycle.
- Stateless API layer: no in-memory session/job state on the FastAPI process
  itself — anything that must persist across requests goes in Postgres or
  Redis, so the API can be horizontally scaled behind a load balancer without
  sticky sessions.
- Database access always goes through connection pooling; no per-request
  connection creation.
- Every list endpoint is paginated by default — never return an unbounded
  result set.
- N+1 queries are treated as bugs: use joins/eager loading, and check new
  endpoints against this before merging.
- Idempotency: task handlers (Celery) must be safe to retry/re-run without
  duplicating side effects (e.g. duplicate fix suggestions on redelivery).
- Rate limiting and backpressure on ingestion: the log-ingestion endpoint
  must not let a burst of incoming logs overwhelm the DB or LLM API — queue
  depth and worker concurrency are the release valve, not unbounded fan-out.
- Structured logging (JSON) with request IDs / correlation IDs on every log
  line, so a single request/error can be traced across API → worker → DB.
- Config via environment variables (12-factor), never hardcoded
  hosts/credentials/model names.

## 3. AI / RAG implementation — must be as accurate as possible, not just "working"

- Every fix suggestion carries a confidence score, and the scoring logic is
  documented — never fabricate a confidence number without a defined basis
  (e.g. retrieval similarity score + LLM self-reported certainty, blended).
- Retrieval quality is measured, not assumed: maintain a small labeled set of
  (error → known-good fix) pairs and check precision/recall of retrieval
  whenever chunking strategy, embedding model, or similarity threshold
  changes. A change that isn't measured isn't considered validated.
- Prompt templates are version-controlled and stored in `llm/`, not
  string-built inline in business logic — a prompt change is a reviewable
  diff, not a buried literal.
- The system must be able to say "I don't know" — low-confidence or
  low-similarity cases must surface as low confidence in the UI, never be
  dressed up as a confident answer. Hallucinated fixes are worse than no
  fix.
- No LLM output is ever auto-applied to code. Every suggestion is a proposed
  diff requiring explicit human approval — this is a hard rule, not a
  configurable default.
- LLM provider calls go through the abstraction in `llm/`, never called
  directly from `backend/` — this keeps prompt/provider changes isolated and
  testable independent of API code.
- Log every LLM request/response (minus secrets) for later evaluation and
  debugging — if a fix suggestion is wrong, we need to be able to see
  exactly what context/prompt produced it.

## 4. "Production-ready" — applies everywhere

- **Tests**: every backend module has unit tests for its core logic; every
  critical user flow (ingest → suggest fix → approve) has at least one
  integration test. No PR merges without passing tests.
- **Error handling**: never swallow exceptions silently. Every external call
  (DB, Redis, git, LLM API) has explicit error handling and a defined
  fallback/retry behavior, not a bare `except: pass`.
- **Security**:
  - All user/log input is validated (Pydantic models) before use — never
    trust log content as safe to execute, template, or interpolate directly
    into a query or shell command.
  - No secrets in code or committed files — environment variables + a
    `.env.example` template, real `.env` gitignored.
  - Parameterized queries only — never string-concatenated SQL (this is
    literally one of our seeded demo bugs, so the tool itself must not repeat
    it).
- **Observability**: health check endpoints for every service; structured
  logs; basic metrics (request latency, queue depth, task failure rate)
  exposed for scraping.
- **Documentation**: every non-obvious decision goes in DECISIONS.md: every
  public API endpoint is documented via FastAPI's automatic OpenAPI docs
  (proper Pydantic models, docstrings, response models — not left as
  untyped dicts).
- **Code review discipline (self-applied)**: before considering a feature
  done, re-read the diff as if reviewing someone else's PR — check for
  unhandled edge cases, missing tests, and whether it matches the standards
  above.

---

## How to use this file

Before writing code for a new piece of frontend/backend/LLM functionality,
re-read the relevant section above. When a shortcut is taken against one of
these standards for time/scope reasons, write it down as a decision (with the
tradeoff) in DECISIONS.md rather than silently deviating.
