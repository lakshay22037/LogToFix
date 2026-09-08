# Log-to-Fix — Dashboard

React + Vite frontend for Log-to-Fix. Lists detected errors and, on the
detail page, shows the correlated commit, stack trace, retrieved similar
past fixes, and the LLM's suggested fix (diff + confidence) — always a
suggestion for human review, never applied automatically.

See the root [SETUP.md](../SETUP.md) for how this fits into the full
local run, and [DECISIONS.md](../DECISIONS.md) for the reasoning behind
the stack choices.

## Running locally

```bash
npm install
npm run dev
```

Runs on `http://localhost:5173`. Copy `.env.example` to `.env` if the
backend isn't at the default `http://localhost:8000`.

## Structure

- `src/api/client.js` — thin fetch wrapper for the backend's `/errors`
  endpoints.
- `src/pages/` — `ErrorListPage`, `ErrorDetailPage`.
- `src/components/` — `ConfidenceBadge`, `DiffViewer`.
