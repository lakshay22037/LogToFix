# Decisions Log

This file records every non-trivial technical decision made on Log-to-Fix — what we
chose, what alternatives we considered, why we picked what we picked, and what
we'd revisit at real production scale. The goal is not to justify the choices —
it's to be able to walk an interviewer through the reasoning like it's a story,
including the parts where we knowingly traded correctness/robustness for
simplicity and can say exactly why.

Format for every entry:

```
## [Date] Decision: <short title>
Chose: ...
Alternatives considered: ... (with a specific reason each was rejected, not just "rejected")
Why we chose this: ...
Tradeoff / what breaks at scale: ...
Interview angle (say this out loud): ...
```

---

## 2026-09-08 Decision: Live log fetching mechanism (file-tailing shipper, decoupled from the app)

Chose: A standalone log-shipper component that tails the demo app's log file
continuously (via the `watchdog` library or a poll-and-read-new-bytes loop,
`tail -f`-style) and forwards new lines to `POST /logs/ingest`, rather than
having the app call the ingestion API directly.

Alternatives considered:
- **Direct push from the app** (app calls `/logs/ingest` itself on every
  error) — rejected because it couples the monitored application to
  Log-to-Fix's existence; a real production service has no idea a
  monitoring tool is watching it, and coupling them here would misrepresent
  how production log monitoring actually works.
- **Polling a remote log store on a fixed interval only** — considered as
  simpler, but rejected as the sole mechanism because it introduces
  detection latency proportional to the poll interval, undermining the
  "live" part of the pitch; file-tailing (or event-driven watching) reacts
  as new lines are written.

Why we chose this: This mirrors how real log monitoring agents work
(Filebeat, Fluentd, Vector, or cloud-native equivalents like CloudWatch Logs
subscriptions) — they watch a log source and forward events, entirely
decoupled from both the application producing logs and the system consuming
them. Building our own lightweight version of that role is what makes the
log source swappable later (see the canonical-schema decision below) without
changing anything downstream.
Tradeoff / what breaks at scale: A single file-tailing process watching one
log file doesn't scale to many services/hosts — real infrastructure runs one
agent per host/container and centralizes via a message bus (Kafka) or a
managed log pipeline. Acceptable here since we're monitoring one demo repo;
flagged as the first thing to replace if this needed to watch multiple
services.
Interview angle: "I built the log shipper as its own decoupled component,
not a function the monitored app calls — that's the same separation real
tools like Filebeat maintain, and it's what lets me swap the log source
later without touching ingestion or processing code."

---

## 2026-09-08 Decision: Canonical log schema + per-source adapters (standardized ingestion)

Chose: Define one canonical internal log event schema (timestamp, level,
service, message, stack_trace, source_type, raw, correlation_id) that every
log event is normalized into before it reaches the core pipeline. Each log
source (local file tail, AWS CloudWatch, Azure Monitor, future sources) gets
its own adapter implementing a common `parse(raw_event) -> NormalizedLogEvent`
interface. Normalization happens at the edge, in the adapter/shipper — the
`POST /logs/ingest` endpoint only ever accepts the canonical schema.

Alternatives considered:
- **Accept raw per-source payloads at the ingestion API and branch on
  `source_type` internally** — rejected because it spreads source-specific
  parsing logic (CloudWatch's JSON shape, Azure Monitor's schema, a raw
  Apache log line) throughout the core pipeline instead of isolating it,
  and makes testing correlation/RAG/LLM logic dependent on faking multiple
  raw formats instead of one clean schema.
- **Require every log source to already emit logs in our exact format** —
  rejected as unrealistic; we don't control the log format of AWS/Azure
  services or arbitrary third-party apps, so the system must adapt to
  sources, not the other way around.
Why we chose this: This is the same idea as OpenTelemetry's receiver/
processor model or a standard ETL "landing zone" — isolate source-specific
variability at the boundary, keep everything downstream (correlation, RAG,
LLM, dashboard) working against one uniform shape. It means adding a new
cloud source later (e.g. GCP Logging) is "write one new adapter," not "touch
the core pipeline."
Tradeoff / what breaks at scale: Every new source requires writing and
maintaining its own adapter — this is a deliberate ongoing cost, traded
against never having source-specific branching logic contaminate the core
pipeline.
Interview angle: "I designed a canonical log schema with per-source adapters
specifically so this could run against AWS, Azure, or a local file
interchangeably — the ingestion API and everything downstream never needs to
know or care where a log actually came from."

---

## 2026-09-08 Finding: Security review pass

A systematic pass over the codebase against ENGINEERING_STANDARDS.md §4,
reported honestly rather than as a blanket "secure" claim.

**Checked and confirmed clean:**
- No secrets in any git-tracked file (`git grep` for Anthropic/OpenAI key
  prefixes across the repo — only in the gitignored `.env`).
- No `shell=True` anywhere — all `subprocess` calls (git operations in
  correlation.py) use argument lists, not shell string interpolation.
- No raw string-formatted SQL outside the intentional demo bug — every real
  query (retrieval.py's pgvector search, all SQLAlchemy ORM operations)
  uses bind parameters.
- Path traversal already guarded in `correlation.py`'s `blame_line`
  (rejects any resolved path outside `repo_root` before running git blame —
  see the original "canonical log schema" and "git-blame correlation"
  decisions).
- Neither the FastAPI app nor the Flask demo app run in debug mode — no
  stack traces leak to clients on an unhandled exception (confirmed
  earlier live: a missing-Redis failure returned a generic "Internal
  Server Error" body, full traceback only in server-side logs).
- All external input is Pydantic-validated (`NormalizedLogEvent`) before
  use.

**Known gaps, deferred deliberately rather than silently:**
- **Rate limiter trusts `request.client.host` directly** — behind a real
  reverse proxy/load balancer, this would be the proxy's IP, not the real
  client's, making per-IP throttling ineffective (or spoofable via
  `X-Forwarded-For` if naively trusted instead). Fine for direct-connection
  local/demo use; needs proper trusted-proxy header handling before a real
  deployment sees traffic through a load balancer — revisit at Phase 6
  (deploy).
- **No CORS configuration yet** — deferred because no frontend exists yet
  to need it; must be added scoped to the frontend's actual origin (never
  a wildcard) when the frontend lands, not copy-pasted from elsewhere.
- **Celery tasks aren't idempotent** — `process_log_event` has no
  dedup key, so a Celery retry (or, per the existing Redis-broker
  reliability tradeoff, redelivery after a Redis restart) would insert a
  duplicate `log_events`/`fix_suggestions` row rather than being a safe
  no-op. Fixing this needs a content-based or explicit dedup key with a
  unique constraint — a real gap against the "idempotency" standard,
  deferred here in favor of load testing and the frontend, but the
  concrete next step if revisited.
Interview angle: "A security pass isn't a checkbox — I can tell you
exactly which of these three gaps I'd fix first if this were going to
production (the rate limiter, since it silently stops working exactly
when you deploy behind a load balancer) and why the other two are lower
priority right now."

---

## 2026-09-08 Decision: Structured JSON logging with cross-process correlation IDs

Chose: A small hand-rolled `JsonFormatter` (`app/logging_config.py`) plus a
`contextvars`-based `correlation_id_var`, wired into both process entry
points (FastAPI, Celery worker) so every log line during a request/task
carries a shared id — required by ENGINEERING_STANDARDS.md's observability
standard ("structured logging with request IDs... traced across API ->
worker -> DB").

A real implementation pitfall, found and fixed rather than assumed away:
calling `logging.basicConfig()` at plain module-import time gets silently
overridden by both frameworks' own logging setup — uvicorn and Celery each
install their own handlers during startup, *after* the app module is
imported. Fixed by hooking each framework's actual documented customization
point instead of guessing at import order:
- **FastAPI**: apply `configure_logging()` inside an `@app.on_event
  ("startup")` handler, which fires after uvicorn's own logging setup.
- **Celery**: use the `after_setup_logger` / `after_setup_task_logger`
  signals to attach `JsonFormatter` to the worker's actual handlers,
  Celery's documented hook for this — a plain `basicConfig()` call is a
  known Celery gotcha for exactly this reason.

`contextvars` don't cross process boundaries, so the correlation id can't
simply be "set once and read anywhere" between the API process and the
worker process — it's carried explicitly on `NormalizedLogEvent
.correlation_id`, generated by API middleware from an incoming
`X-Request-ID` header (or a new UUID), returned to the client in the
response header, and re-applied to the worker's own contextvar at the start
of `process_log_event`.

Verified end-to-end: a request sent with `X-Request-ID: trace-across-
services-456` produced matching `correlation_id` fields in both the API's
JSON log line and the worker's JSON log line for the same event — confirmed
by grepping both process logs for the same id.
Interview angle: "I didn't just add a JSON formatter and assume it worked —
I found that both uvicorn and Celery silently override logging config set
at import time, and fixed it using each framework's actual hook rather than
guessing at initialization order."

---

## 2026-09-08 Decision: Rate limiting on ingestion — Redis fixed-window counter

Chose: A hand-rolled fixed-window rate limiter (`app/rate_limit.py`) using
Redis `INCR`/`EXPIRE` keyed by client IP and time window, applied to
`POST /logs/ingest` as a FastAPI dependency.
Alternatives considered:
- **In-memory counter (e.g. a dict on the FastAPI process)** — rejected
  because it violates the stateless-API standard: state wouldn't be shared
  across horizontally scaled API instances, so a client could bypass the
  limit just by landing on a different instance.
- **A rate-limiting library (e.g. `slowapi`)** — rejected in favor of a
  small hand-rolled version here specifically because our need (protect one
  endpoint from bursts) is simple enough not to need a library's per-route
  decorator configurability, and hand-rolling it means no unfamiliar
  library behavior to verify — the whole implementation is ~20 lines,
  reusing the Redis connection we already run.
Why we chose this: Redis is already a required dependency (Celery broker),
so this adds no new infrastructure — just a new use of it. Fixed-window
counters are the simplest correct implementation for "cap requests per
IP per time window."
Tradeoff / what breaks at scale: Fixed windows allow up to 2x the stated
limit in a burst that straddles a window boundary (e.g. a burst at 0:59 and
another at 1:01 could both hit the limit in the same ~2 seconds). A sliding
window or token bucket would be more precise; not worth the extra
complexity at this project's traffic scale, but the first thing to swap in
under real abuse-prevention requirements.
Interview angle: "I picked the simplest correct rate limiter — a Redis
fixed-window counter — over a library, specifically because I could verify
every line of it myself. I know its precise weakness (boundary bursts) and
what I'd replace it with (a sliding window) if that mattered here."

Verified via real HTTP requests against a running server: with the limit
set to 5/window, requests 1-5 returned 202 and requests 6+ returned 429,
confirming the dependency actually gates the endpoint end-to-end, not just
in isolation.

---

## 2026-09-08 Finding: Breadth — git-blame correlation for non-exception bugs

To bring the race-condition and N+1 seeded bugs into the pipeline (they
don't raise exceptions, so had no stack trace for correlation to use), used
Python's `logging` `stack_info=True` option to attach a captured stack even
without a raised exception — no changes needed to the adapter/correlation
regex, since the frame format (`File "...", line N, in func`) is identical.

Result differs sharply by bug type:
- **N+1 (reports)**: correlates correctly — blames `1e55abd`, the exact
  commit that seeded the bug. The `log_reports.warning(...)` call lives
  inside the same function, added in the same commit, as the N+1 query
  loop it's warning about.
- **Race condition (counter)**: correlates *technically correctly, but
  practically uselessly* — blames `45305b4`, the very first walking-skeleton
  commit, not `3237941` (the commit that actually removed the lock and
  introduced the race). Root cause: `check_counter`'s mismatch-detection
  code — where the error is logged — predates the race-condition bug
  entirely; the bug was introduced by removing a lock inside a *different*
  function (`increment_counter`). Git blame is correct that the log-call
  line itself hasn't changed since the first commit — it just isn't the
  line responsible for the bug.

Why this isn't "fixed" further: the fundamental issue isn't the log
statement's placement — a lost update is only observable by comparing
against an external expected value, which structurally has to happen away
from the faulty read-modify-write. Moving the log call doesn't change that.

This is left as a documented, real limitation rather than special-cased
away: git-blame-from-log-statement correlation only works when the
detection site and the fault site are the same commit's work. For
symptom-detected bugs (races, some invariant violations) where an
older, unrelated piece of monitoring code happens to be what logs the
symptom, this technique attributes blame to whoever last touched the
*detection* code, which can be arbitrarily unrelated to the actual fault.
Interview angle: "I found and kept a real failure case of my own
correlation technique instead of hiding it — it's the same distinction
production debugging always deals with: where an error is *observed* isn't
always where it's *caused*. A more capable version of this tool would need
execution tracing (which functions actually ran in the failing request),
not just static blame on the log statement's line."

---

## 2026-09-08 Finding: Measured RAG retrieval quality — labeled eval set

Built `data/rag_eval_set.json`: 15 hand-written paraphrases of real seeded
SWE-bench bugs (e.g. "sqlmigrate command always wraps SQL output in BEGIN/
COMMIT even for databases without transactional DDL support" for
`django-11039`), each labeled with the source it should retrieve. Paraphrased
rather than copied verbatim, so the eval measures genuine semantic
retrieval, not exact-text lookup. `backend/scripts/eval_retrieval.py` runs
every case through the real embedding + retrieval pipeline and reports
Hits@1 / Hits@3 / Hits@k / MRR.

Measured result (OpenAI `text-embedding-3-small`, 25-example corpus,
top_k=5): **Hits@1 = 100%, Hits@3 = 100%, MRR = 1.000** — every single
paraphrase retrieved its true match as the #1 result.

Why this is a real result and not just a vanity number: earlier in this
same session, a test-harness bug (env vars not loading in a standalone
script — see the ".env loading" fix) produced a misleadingly bad ranking
(true match 19th of 25) purely from comparing a fake query vector against
real corpus vectors. Once fixed, both the earlier spot-checks and now this
full labeled eval independently confirm retrieval is genuinely strong —
this wasn't cherry-picked after the fact.

Honest caveat — what this eval does *not* yet prove: at only 25 corpus
examples covering clearly distinct bugs, and with paraphrases that retain
distinctive technical vocabulary from the original (`separability_matrix`,
`sqlmigrate`, `FilePathField`, ...), there's very little competition for the
top spot. A 100% score here is a real, measured floor — not evidence that
retrieval would stay this strong with (a) a much larger, more topically
overlapping corpus, (b) near-duplicate bugs genuinely competing for rank 1,
or (c) queries using different vocabulary than the original report (e.g. an
end-user's plain-English error description vs. a maintainer's technical
issue text).
Interview angle: "I don't just report a retrieval eval score — I can tell
you exactly what it does and doesn't prove, and what I'd need to add
(harder negatives, a bigger corpus, vocabulary-mismatched queries) to trust
it at production scale."

---

## 2026-09-08 Decision: Embedding model for RAG — OpenAI text-embedding-3-small

Chose: OpenAI's `text-embedding-3-small` (1536 dimensions) to embed bug
descriptions and past fixes for pgvector similarity search.
Alternatives considered:
- **Local, free (sentence-transformers `all-MiniLM-L6-v2`)** — zero cost, no
  external dependency, works offline. Rejected as the choice here (though
  it's a legitimate option) in favor of the higher retrieval quality a
  hosted model gives, since retrieval quality is the thing Phase 2 is meant
  to be measured and tuned on — a weaker embedding model makes that
  measurement less meaningful.
- **Voyage AI** (Anthropic's recommended embedding partner, code-optimized
  models) — also viable, rejected only to avoid a third external provider
  account/API key on top of Anthropic and OpenAI.
Why we chose this: `text-embedding-3-small` is inexpensive (~$0.02/1M
tokens), well-documented, and 1536 dimensions matches the `vector(1536)`
column already migrated in `fix_examples` — no schema change needed.
Tradeoff / what breaks at scale: introduces a second paid provider
dependency (OpenAI) alongside Claude — acceptable here since embedding calls
are one-time (seeding the corpus) plus one per incoming error, not a
per-token-heavy workload like the LLM fix generation itself.
Interview angle: "I picked a hosted embedding model specifically because
Phase 2's goal is to measure and tune retrieval quality — using the
free/local option would have made it harder to tell whether a bad result
was the embedding model's fault or the chunking/threshold choices I was
actually trying to evaluate."

Implementation note: mirrors the LLM client's provider pattern exactly —
`EMBEDDING_PROVIDER` env var defaults to `fake` (a deterministic hash-based
embedder, zero cost, mechanism-only — not meaningful for similarity
quality), set to `openai` for real embeddings. Same reasoning as the LLM
FakeClient: no free tier for OpenAI's API either, so development shouldn't
require spending real money by default.

---

## 2026-09-08 Decision: Data sourcing strategy (three separate sources, not one)

Chose: Use three data sources for three distinct purposes, not one unified
dataset:
1. **Our own seeded demo repo** (`data/demo-repo/`) — the live error source.
   A small Python app we write ourselves, with intentionally seeded bugs
   (SQL injection, missing validation, off-by-one, race condition, N+1).
   Running it (or a script that periodically triggers its bugs) produces the
   log lines that flow through ingestion → git-blame correlation.
2. **Loghub** — reference only, for realistic log *format*/parsing patterns
   (e.g. how a real Apache/HDFS log line is structured). Not wired into the
   live pipeline directly.
3. **BugsInPy / SWE-bench** — the RAG corpus. 20-30 real (error → fix) pairs
   from real Python projects, embedded into pgvector as the "has a similar
   bug been fixed before" reference set used in Phase 2.

Alternatives considered:
- **Use Loghub logs as the live error stream directly** — rejected because
  Loghub logs aren't attached to any codebase we have access to; `git blame`
  correlation requires errors that trace back to a repo whose history we
  control. Loghub logs would dead-end at the correlation step.
- **Use BugsInPy/SWE-bench repos themselves as the "live" monitored repo**
  instead of a custom demo repo — considered, since it would mean real
  historical bugs and real fix history in one place. Rejected because these
  repos are large, unfamiliar, and not designed to run standalone or emit
  logs on demand — seeding our own small repo gives full control over
  making errors reproducible and demoable on command, which matters more
  for demo reliability than dataset "realism."
- **Skip real datasets entirely and only use synthetic bugs** — rejected
  because BugsInPy/SWE-bench fix pairs materially strengthen the RAG story
  (real-world fix patterns instead of only ones we invented ourselves), and
  Loghub format patterns make the log parser more realistic than inventing
  a log format from scratch.

Why we chose this: Each dataset is used for exactly the property it's
actually good for — Loghub for format realism, BugsInPy/SWE-bench for a real
historical-fix corpus, and a custom repo for the one thing neither dataset
can provide: a controllable, git-history-attached live error source that we
can seed and reproduce on demand.
Tradeoff / what breaks at scale: The custom demo repo means our seeded bugs
are somewhat "toy" compared to production-scale bug complexity — acceptable
here since demo reproducibility matters more than bug realism, but worth
being upfront about if asked "are these real production bugs?"
Interview angle: "I used three data sources deliberately, not because I
couldn't find one dataset that did everything, but because no single
dataset could satisfy live-error-generation, realistic log formatting, and
a historical-fix RAG corpus at the same time — each needed a source suited
to that specific property."

---

## 2026-09-08 Decision: Project execution flow (walking skeleton, then deepen)

Chose: Build a thin, fully-working end-to-end slice first (one error type,
minimal scope, no RAG, no polish), then deepen it in phases: RAG → breadth
(more bug types) → hardening (tests/security/observability) → load testing →
deploy/CI → interview packaging. Full phase breakdown:

0. Foundation (seeded demo repo, docker-compose skeleton, .gitignore/.env)
1. Walking skeleton — ingest → git-blame correlate → LLM fix (no RAG) →
   dashboard, for one error type only
2. RAG — embeddings, pgvector, retrieval, measured against a labeled eval set
3. Breadth — add remaining seeded bug types through the now-proven pipeline
4. Hardening — tests, structured logging, rate limiting, security pass
5. Load testing — real numbers on where it actually breaks
6. Deploy + CI
7. Interview packaging — README, architecture diagram, STAR stories

Alternatives considered:
- **Layer-by-layer** (build all of `frontend/` fully, then all of `backend/`,
  then all of `llm/`) — rejected because nothing is actually testable
  end-to-end until every layer is finished; integration problems (e.g. "how
  do I map a stack trace to a git blame result reliably") would only surface
  in the final week, when they're most expensive to fix and least fun to
  discover under time pressure.
- **Feature-complete-per-bug-type** (fully build ingest→fix→RAG→dashboard for
  the SQL injection bug, then repeat fully for the next bug type, etc.) —
  rejected because it means re-solving the same infra problems (queueing,
  git correlation, LLM prompting) repeatedly instead of proving them once
  and reusing them; it also delays RAG (the highest-learning-value part)
  until after several bug types are already fully built.
- **RAG-first** (build the RAG/embedding pipeline before a working ingest→fix
  pipeline exists) — rejected because RAG has nothing to retrieve *into* yet
  without a working correlation + fix-generation path; building it first
  means building and testing it against fabricated inputs instead of real
  ones.

Why we chose this: This is the "walking skeleton" pattern (build the
thinnest possible version of the entire system first, prove every
architectural decision — queue, git integration, LLM call, DB — actually
works together, then add depth/breadth incrementally). It front-loads
integration risk instead of deferring it, and it means at every phase
boundary there is a demoable, working system rather than a pile of
half-finished layers.
Tradeoff / what breaks at scale: The walking skeleton's Phase 1 code (e.g.
the git correlation logic, the LLM prompt) is deliberately minimal and will
likely need rework once RAG and multiple bug types are added — we're
accepting some rework cost in exchange for de-risking integration early and
having something demoable at every step. This is intentional, not technical
debt from carelessness.
Interview angle: "I built a walking skeleton first — the thinnest possible
version of the full pipeline — specifically so integration risk (queueing,
git correlation, LLM calls, DB writes all working together) surfaced in week
one instead of week six, when it would've been far more expensive to
untangle."

---

## 2026-09-08 Decision: Overall stack

### Frontend — React (Vite)
Chose: React with Vite as the build tool
Alternatives considered:
- Plain HTML/JS — rejected because a diff viewer + dashboard with live status
  updates needs component state management; hand-rolling that is wasted effort
  for a project meant to showcase engineering judgment, not masochism.
- Vue / Svelte — both are technically strong (Svelte especially — smaller
  bundles, less boilerplate), rejected only because React has broader industry
  adoption, so the patterns (hooks, state management, component composition)
  are more directly transferable to what an interviewer's own stack likely
  looks like.
- Create React App instead of Vite — rejected because CRA is effectively
  unmaintained; Vite has faster dev-server startup/HMR and is the current
  default recommendation.
Why we chose this: Maximize interview relevance and ecosystem support
(react-diff-viewer for the fix diff, recharts for confidence/error trend
charts) over minimizing bundle size or boilerplate.
Tradeoff / what breaks at scale: None specific to React itself at our scale —
the real scaling concern for a dashboard like this is state/data-fetching
patterns (polling vs. websockets) as error volume grows, not the framework.
Interview angle: "I picked React not because it's technically superior to
Svelte for this size of app, but because I optimized for demonstrating
patterns that transfer directly to how most engineering orgs already build
frontends."

### Backend API — FastAPI (Python)
Chose: FastAPI
Alternatives considered:
- Flask — rejected because it has no native async support and no built-in
  request/response validation; we'd have to bolt on Pydantic and an async
  WSGI/ASGI setup manually, which FastAPI gives for free.
- Django REST Framework — rejected as overkill; DRF's strength is admin
  panels, ORM-heavy CRUD apps, and batteries-included auth — none of which is
  the hard part of this project. It would add weight without adding value.
- Node/Express — rejected specifically to keep backend + worker + LLM code in
  one language (Python), since Python has by far the strongest ecosystem for
  embeddings, pgvector clients, and git tooling (GitPython). Splitting
  language by service would mean maintaining two dependency ecosystems for a
  solo project.
Why we chose this: The system is fundamentally I/O-bound (waiting on DB
queries, LLM API calls, git operations) — FastAPI's native async/await maps
directly onto that, plus automatic OpenAPI docs and Pydantic validation come
free and reduce boilerplate.
Tradeoff / what breaks at scale: FastAPI's async model requires discipline —
a single blocking call (e.g. a sync git subprocess call) inside an async
route can stall the whole event loop. We mitigate this by pushing genuinely
slow work (git blame, embeddings, LLM calls) into Celery workers rather than
doing it inline in request handlers.
Interview angle: "I chose FastAPI specifically because the workload is I/O
bound, not CPU bound — async gives real throughput benefit here, unlike a
CPU-heavy service where it wouldn't matter."

### Async task queue — Redis + Celery
Chose: Redis as the Celery broker/result backend, Celery for background
workers
Alternatives considered:
- Synchronous processing (do everything inline in the ingest request) —
  rejected because git blame + embedding lookup + LLM call can easily take
  several seconds combined; blocking the log-ingestion endpoint on that would
  make ingestion the bottleneck and risk dropping/timing out incoming log
  events under any real load.
- RabbitMQ as the broker — rejected for this project specifically because of
  operational simplicity: Redis is a single lightweight container we already
  need (also usable as a cache later, e.g. caching git blame results), while
  RabbitMQ adds another moving part with its own protocol and management UI
  for a demo-scale system that doesn't need its stronger guarantees yet.
- AWS SQS — rejected because it ties local development to a live AWS account/
  network access; Redis runs identically in Docker Compose locally and in
  deployment, which matters for a project meant to be easy to demo end-to-end.
Why we chose this: Decouples slow processing from fast ingestion, and Celery
is the most common Python task queue — well documented, easy to reason about
retries/task routing.
Tradeoff / what breaks at scale: Redis-as-broker has weaker delivery
guarantees than RabbitMQ — if Redis restarts, in-flight/queued tasks can be
lost (no durable disk-backed queue by default). At production scale with
real error-processing SLAs, RabbitMQ (or SQS with dead-letter queues) would
be the correct choice. This is a deliberate, documented "known weaker point"
of the architecture, not an oversight.
Interview angle: "I know Redis-as-broker isn't the production-grade choice —
I picked it because at this scale losing a queued task on a Redis restart is
an acceptable risk, but I can tell you exactly what I'd swap in (RabbitMQ)
and why, if reliability requirements went up."

### Primary datastore — PostgreSQL + pgvector
Chose: PostgreSQL with the pgvector extension for a single unified datastore
Alternatives considered:
- A dedicated vector database (Pinecone, Weaviate, Qdrant) alongside Postgres
  for relational data — rejected because running two databases means keeping
  them in sync (e.g. deleting an error's relational row but orphaning its
  vector row), which is real operational complexity not justified at our
  scale (tens/hundreds of embedded fix examples, not millions).
- MongoDB — rejected because our data is fundamentally relational (errors
  belong to repos, fixes reference errors, confidence scores reference fixes)
  — forcing that into documents would mean re-implementing joins in
  application code for no benefit.
Why we chose this: One database, one connection pool, one backup strategy,
transactional consistency between "this fix was generated" and "this fix's
embedding was stored." pgvector's IVFFlat/HNSW indexing is sufficient at
demo scale.
Tradeoff / what breaks at scale: pgvector's similarity search degrades
compared to purpose-built vector DBs as embedding count grows into the
millions, and it doesn't have the same metadata-filtering sophistication.
This is the single most likely "what would you change for a real product"
answer we should have ready.
Interview angle: "I unified on Postgres+pgvector because at this scale the
operational cost of a second database outweighs pgvector's performance gap —
but I benchmarked our actual similarity search latency so I have a real
number, not a guess, for when that tradeoff would flip."

### LLM provider — Claude, with a provider-agnostic interface (also supports OpenAI)
Chose: Claude as primary provider, behind an interface abstraction that also
supports OpenAI
Alternatives considered:
- Hardcoding a single provider directly into business logic — rejected
  because it's a well-known anti-pattern (vendor lock-in, untestable without
  hitting a real paid API) and because demonstrating a clean provider
  abstraction is itself a system-design signal worth having.
- Self-hosting an open-source model (e.g. via Ollama/vLLM) — rejected for
  this project because code-reasoning quality on "read this stack trace, this
  function, these 3 past fixes, propose a diff" tasks is meaningfully weaker
  on most open models we could run locally, and the cost of Claude/OpenAI API
  calls at demo volume is negligible — so we're not solving a cost problem
  that exists here.
Why we chose this: Claude's long context and code-reasoning quality suit
grounded fix-suggestion tasks well; the provider interface lets us swap or
A/B test providers without touching calling code.
Tradeoff / what breaks at scale: At high volume, LLM API cost and rate limits
become real constraints — this is where self-hosting or a cheaper/smaller
model for a first-pass triage (only escalating to Claude for high-value
cases) would become worth it.
Interview angle: "I built the LLM client behind an interface on purpose,
even as a solo project — it's the boundary I'd expect to change most often
(new model, cost optimization, fallback provider), so I isolated it."

### Code correlation — direct git operations against a locally cloned repo
Chose: GitPython / shelling out to `git` against a repo cloned/cached locally
Alternatives considered:
- GitHub API for blame/history lookups — rejected because it's rate-limited
  and network-latency-bound per call; for a monitoring tool doing this
  correlation potentially many times a minute, that latency and rate-limit
  risk is a real bottleneck a local clone avoids entirely.
Why we chose this: `git blame` and history walking are fast and rich against
a local clone, and we control the one demo repo being monitored, so clone-once
+ periodic `git pull` is simple and sufficient.
Tradeoff / what breaks at scale: This only works cleanly for a small number
of known repos. If Log-to-Fix needed to support arbitrary customer repos,
we'd need a repo-cache eviction/sync strategy (LRU cache of clones, webhook-
triggered pulls instead of polling) — noted as a real scaling question we
chose not to solve here because it's out of scope for a single demo repo.
Interview angle: "I picked local clone + pull over the GitHub API purely on
latency and rate-limit grounds — for one repo it's a non-issue, but I can
describe exactly what a multi-repo cache layer would need to look like."

### Containerization + deployment — Docker Compose → AWS/Azure, GitHub Actions for CI
Chose: Docker Compose for local orchestration, deployed to AWS (ECS or EC2)
or Azure, CI via GitHub Actions
Alternatives considered:
- Kubernetes — rejected as disproportionate: K8s' value shows up when you
  have many services, multiple teams, and need things like auto-scaling
  policies, rolling deploy strategies across a large fleet — none of which
  applies to a ~4-service solo project. Using it here would mostly demonstrate
  YAML tolerance, not system-design judgment.
- Manual VM setup without containers — rejected because it removes the
  "identical environment locally and in deployment" guarantee that Docker
  gives us, and reintroduces "works on my machine" risk.
- No CI at all — rejected outright; CI is table stakes and GitHub Actions is
  free and the most commonly used tool, so it's directly resume-relevant.
Why we chose this: Docker Compose demonstrates real multi-service
orchestration (frontend, backend, worker, Redis, Postgres) at a complexity
level matched to the project's actual scale.
Tradeoff / what breaks at scale: Docker Compose has no orchestration
features (auto-restart policies across hosts, rolling deploys, auto-scaling)
— at real multi-instance/multi-team scale, Kubernetes or a managed
equivalent (ECS Fargate with auto-scaling) becomes the right call. We treat
this as a "know when you'd graduate" answer, not a gap.
Interview angle: "I deliberately didn't reach for Kubernetes — I can explain
what specific problems it solves that Compose can't, and why none of those
problems exist yet at this project's scale."

---

## 2026-09-08 Decision: Top-level folder structure

Chose: four top-level folders — `frontend/`, `backend/`, `data/`, `llm/` —
plus root-level `docker-compose.yml`, `DECISIONS.md`, `README.md`.

Alternatives considered:
- Flat structure (no top-level folders, everything in root) — rejected
  because it becomes unreadable past the thin end-to-end slice; there'd be no
  visual signal of where responsibility boundaries are.
- Split by language (`python/`, `js/`) instead of responsibility — rejected
  because it would bury the LLM/RAG logic inside a generic `python/` folder
  alongside API routing code, hiding the part of the system most worth
  highlighting in an interview walkthrough.
- A fifth top-level `worker/` folder for Celery tasks — considered, but
  rejected for now; the worker is currently thin enough to live inside
  `backend/`. Flagged below as a likely future split.

Why we chose this: The split mirrors a responsibility boundary, not a
language boundary — each folder answers a different question in the
pipeline:
- `frontend/` — how results are shown (dashboard, diff viewer)
- `backend/` — how requests/ingestion/API/background workers are served
- `data/` — what the system operates on (seeded demo repo with intentional
  bugs, log fixtures, DB schema/migrations) — i.e. inputs/state, not behavior
- `llm/` — how fixes are reasoned about (prompts, embeddings, RAG retrieval,
  provider clients) — isolated specifically because this is the riskiest,
  most-iterated-on part of the system (see Step 6, RAG tuning) and we want to
  test/swap it independently of API code.

Tradeoff / what breaks at scale: If the Celery worker logic grows
significantly (e.g. many distinct task types, its own retry/monitoring
concerns), it should be split out of `backend/` into its own `worker/`
top-level folder — noted here so it's a deliberate future decision, not
scope creep discovered mid-build.
Interview angle: "I organized by responsibility instead of by language
specifically so the RAG/LLM logic — the part most worth discussing — has its
own clear boundary instead of being buried inside a generic backend folder."
