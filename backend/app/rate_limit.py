import os
import time
from typing import Optional

import redis
from fastapi import HTTPException, Request

from app.celery_app import REDIS_URL

_redis_client: Optional[redis.Redis] = None

RATE_LIMIT_MAX_REQUESTS = int(os.environ.get("INGEST_RATE_LIMIT_MAX", "100"))
RATE_LIMIT_WINDOW_SECONDS = int(os.environ.get("INGEST_RATE_LIMIT_WINDOW_SECONDS", "60"))


def get_redis_client() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.Redis.from_url(REDIS_URL)
    return _redis_client


def enforce_rate_limit(request: Request) -> None:
    """Fixed-window rate limit keyed by client IP, backed by Redis (the
    broker we already run) rather than per-process memory — required by the
    stateless-API standard, since an in-memory counter wouldn't be shared
    across horizontally scaled API instances. See DECISIONS.md: "Rate
    limiting on ingestion" for the fixed-window-vs-token-bucket tradeoff."""
    client_ip = request.client.host if request.client else "unknown"
    window = int(time.time() // RATE_LIMIT_WINDOW_SECONDS)
    key = f"ratelimit:ingest:{client_ip}:{window}"

    client = get_redis_client()
    current = client.incr(key)
    if current == 1:
        client.expire(key, RATE_LIMIT_WINDOW_SECONDS)

    if current > RATE_LIMIT_MAX_REQUESTS:
        raise HTTPException(status_code=429, detail="Rate limit exceeded, try again later")
