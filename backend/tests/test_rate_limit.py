import pytest
import redis
from fastapi import HTTPException
from starlette.datastructures import Address
from starlette.requests import Request

from app.rate_limit import RATE_LIMIT_MAX_REQUESTS, enforce_rate_limit, get_redis_client


def _redis_reachable() -> bool:
    try:
        get_redis_client().ping()
        return True
    except redis.exceptions.ConnectionError:
        return False


requires_redis = pytest.mark.skipif(not _redis_reachable(), reason="Redis not reachable")


def _fake_request(client_ip: str) -> Request:
    scope = {
        "type": "http",
        "client": (client_ip, 12345),
        "headers": [],
    }
    return Request(scope)


@requires_redis
def test_allows_requests_under_the_limit():
    request = _fake_request("10.0.0.1")
    for _ in range(5):
        enforce_rate_limit(request)  # should not raise


@requires_redis
def test_blocks_requests_over_the_limit():
    request = _fake_request("10.0.0.2")
    for _ in range(RATE_LIMIT_MAX_REQUESTS):
        enforce_rate_limit(request)

    with pytest.raises(HTTPException) as exc_info:
        enforce_rate_limit(request)
    assert exc_info.value.status_code == 429


@requires_redis
def test_different_ips_have_independent_limits():
    request_a = _fake_request("10.0.0.3")
    request_b = _fake_request("10.0.0.4")

    for _ in range(RATE_LIMIT_MAX_REQUESTS):
        enforce_rate_limit(request_a)

    enforce_rate_limit(request_b)  # different IP — should not raise
