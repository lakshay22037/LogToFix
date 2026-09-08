# Demo Repo — seeded target application

A small Flask app used as the live target for Log-to-Fix. It has five
intentionally seeded bugs, each representative of a real-world bug category,
so the pipeline (ingest → git-blame correlate → RAG → LLM fix suggestion) has
a genuine mix of problems to detect and reason about.

## Seeded bugs

| Endpoint | Bug category | What goes wrong |
|---|---|---|
| `GET /orders/<order_id>` | SQL injection | Query built via string formatting instead of parameterization; a malformed `order_id` breaks the query and raises `sqlite3.OperationalError` |
| `POST /users` | Missing input validation | Assumes `email` key exists in the JSON body with no check; missing key raises `KeyError` |
| `GET /items/page/<page>` | Off-by-one | Pagination slice bounds are wrong by one, raising `IndexError` on the last page |
| `POST /counter/increment` | Race condition | Global counter incremented non-atomically; concurrent requests lose updates, detected and logged as a mismatch |
| `GET /reports/summary` | N+1 query | Loops over every order and issues one DB query per order instead of a join; logged as a slow-query warning past a threshold |

## Running it

```
pip install -r requirements.txt
python app.py
```

Logs are written to `logs/app.log` in a semi-realistic plain-text format:

```
2026-09-08 10:22:31,120 ERROR [orders] Failed to fetch order 4521': near "'": syntax error
```

## Simulating live traffic

```
python traffic_generator.py
```

Continuously hits every endpoint, occasionally with bad input, so the app
produces a steady stream of both normal and error log lines — this is the
"live production log" source that the file-tail shipper (see `backend/`)
watches.
