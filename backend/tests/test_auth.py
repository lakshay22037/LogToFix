import time

import jwt
import pytest
from fastapi import HTTPException

from app import auth

TEST_SECRET = "test-secret-not-real"


def _make_token(secret=TEST_SECRET, sub="user-123", email="test@example.com", audience="authenticated", exp_delta=3600):
    payload = {
        "sub": sub,
        "email": email,
        "aud": audience,
        "exp": int(time.time()) + exp_delta,
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def test_valid_token_returns_current_user(monkeypatch):
    monkeypatch.setattr(auth, "SUPABASE_JWT_SECRET", TEST_SECRET)
    token = _make_token()

    user = auth.get_current_user(authorization=f"Bearer {token}")

    assert user.id == "user-123"
    assert user.email == "test@example.com"


def test_missing_header_raises_401(monkeypatch):
    monkeypatch.setattr(auth, "SUPABASE_JWT_SECRET", TEST_SECRET)
    with pytest.raises(HTTPException) as exc_info:
        auth.get_current_user(authorization=None)
    assert exc_info.value.status_code == 401


def test_malformed_header_raises_401(monkeypatch):
    monkeypatch.setattr(auth, "SUPABASE_JWT_SECRET", TEST_SECRET)
    with pytest.raises(HTTPException) as exc_info:
        auth.get_current_user(authorization="NotBearer sometoken")
    assert exc_info.value.status_code == 401


def test_wrong_secret_raises_401(monkeypatch):
    monkeypatch.setattr(auth, "SUPABASE_JWT_SECRET", TEST_SECRET)
    token = _make_token(secret="a-different-secret")

    with pytest.raises(HTTPException) as exc_info:
        auth.get_current_user(authorization=f"Bearer {token}")
    assert exc_info.value.status_code == 401


def test_expired_token_raises_401(monkeypatch):
    monkeypatch.setattr(auth, "SUPABASE_JWT_SECRET", TEST_SECRET)
    token = _make_token(exp_delta=-3600)  # already expired

    with pytest.raises(HTTPException) as exc_info:
        auth.get_current_user(authorization=f"Bearer {token}")
    assert exc_info.value.status_code == 401


def test_wrong_audience_raises_401(monkeypatch):
    monkeypatch.setattr(auth, "SUPABASE_JWT_SECRET", TEST_SECRET)
    token = _make_token(audience="not-authenticated")

    with pytest.raises(HTTPException) as exc_info:
        auth.get_current_user(authorization=f"Bearer {token}")
    assert exc_info.value.status_code == 401


def test_missing_server_secret_raises_500(monkeypatch):
    monkeypatch.setattr(auth, "SUPABASE_JWT_SECRET", None)
    token = _make_token()

    with pytest.raises(HTTPException) as exc_info:
        auth.get_current_user(authorization=f"Bearer {token}")
    assert exc_info.value.status_code == 500
