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
