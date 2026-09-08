# Log-to-Fix — Project Instructions

This file is auto-loaded into context at the start of every session in this repo.
It exists so the two documents below are never skipped by accident.

## Always read before writing code

- **[ENGINEERING_STANDARDS.md](ENGINEERING_STANDARDS.md)** — the bar for
  frontend responsiveness, backend scalability, AI/RAG accuracy, and
  production-readiness (tests, error handling, security, observability).
  Before writing or editing code in `frontend/`, `backend/`, `data/`, or
  `llm/`, re-read the relevant section and hold new code to it.

- **[DECISIONS.md](DECISIONS.md)** — the log of every non-trivial technical
  decision, with alternatives considered and tradeoffs. Before making a
  choice of technology, library, or architecture pattern, check whether it's
  already been decided here. After making a new non-trivial decision, or
  knowingly deviating from ENGINEERING_STANDARDS.md for scope/time reasons,
  add an entry here in the same format (Chose / Alternatives considered /
  Why / Tradeoff / Interview angle).

## Working agreement

- This project is a learning + resume vehicle: correctness, security, and
  scalability tradeoffs are the point, not just shipping a feature. When
  there's a meaningful tradeoff, surface it rather than silently picking one
  side.
- No LLM-generated fix is ever auto-applied to code — always a proposed diff
  requiring human approval. This is a hard rule (see
  ENGINEERING_STANDARDS.md §3).
- When a shortcut is taken against a standard (e.g. skipping pagination on a
  first pass), say so and log it in DECISIONS.md rather than deviating
  silently.
