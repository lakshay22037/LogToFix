import time

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi import HTTPException

from app import auth


def _generate_keypair():
    private_key = ec.generate_private_key(ec.SECP256R1())
    return private_key, private_key.public_key()


class _FakeSigningKey:
    def __init__(self, key):
        self.key = key


class _FakeJWKSClient:
    """Stands in for jwt.PyJWKClient — returns a fixed public key instead of
    fetching from a real JWKS endpoint over the network."""

    def __init__(self, public_key):
        self._public_key = public_key

    def get_signing_key_from_jwt(self, token):
        return _FakeSigningKey(self._public_key)


def _make_token(private_key, sub="user-123", email="test@example.com", audience="authenticated", exp_delta=3600):
    payload = {
        "sub": sub,
        "email": email,
        "aud": audience,
        "exp": int(time.time()) + exp_delta,
    }
    return jwt.encode(payload, private_key, algorithm="ES256")


def test_valid_token_returns_current_user(monkeypatch):
    private_key, public_key = _generate_keypair()
    monkeypatch.setattr(auth, "_JWKS_CLIENT", _FakeJWKSClient(public_key))
    token = _make_token(private_key)

    user = auth.get_current_user(authorization=f"Bearer {token}")

    assert user.id == "user-123"
    assert user.email == "test@example.com"


def test_missing_header_raises_401(monkeypatch):
    _, public_key = _generate_keypair()
    monkeypatch.setattr(auth, "_JWKS_CLIENT", _FakeJWKSClient(public_key))
    with pytest.raises(HTTPException) as exc_info:
        auth.get_current_user(authorization=None)
    assert exc_info.value.status_code == 401


def test_malformed_header_raises_401(monkeypatch):
    _, public_key = _generate_keypair()
    monkeypatch.setattr(auth, "_JWKS_CLIENT", _FakeJWKSClient(public_key))
    with pytest.raises(HTTPException) as exc_info:
        auth.get_current_user(authorization="NotBearer sometoken")
    assert exc_info.value.status_code == 401


def test_wrong_key_raises_401(monkeypatch):
    # Token signed by one keypair, verified against a different one's
    # public key — simulates a forged/tampered token.
    signing_private_key, _ = _generate_keypair()
    _, different_public_key = _generate_keypair()
    monkeypatch.setattr(auth, "_JWKS_CLIENT", _FakeJWKSClient(different_public_key))
    token = _make_token(signing_private_key)

    with pytest.raises(HTTPException) as exc_info:
        auth.get_current_user(authorization=f"Bearer {token}")
    assert exc_info.value.status_code == 401


def test_expired_token_raises_401(monkeypatch):
    private_key, public_key = _generate_keypair()
    monkeypatch.setattr(auth, "_JWKS_CLIENT", _FakeJWKSClient(public_key))
    token = _make_token(private_key, exp_delta=-3600)  # already expired

    with pytest.raises(HTTPException) as exc_info:
        auth.get_current_user(authorization=f"Bearer {token}")
    assert exc_info.value.status_code == 401


def test_wrong_audience_raises_401(monkeypatch):
    private_key, public_key = _generate_keypair()
    monkeypatch.setattr(auth, "_JWKS_CLIENT", _FakeJWKSClient(public_key))
    token = _make_token(private_key, audience="not-authenticated")

    with pytest.raises(HTTPException) as exc_info:
        auth.get_current_user(authorization=f"Bearer {token}")
    assert exc_info.value.status_code == 401


def test_missing_server_config_raises_500(monkeypatch):
    monkeypatch.setattr(auth, "_JWKS_CLIENT", None)
    private_key, _ = _generate_keypair()
    token = _make_token(private_key)

    with pytest.raises(HTTPException) as exc_info:
        auth.get_current_user(authorization=f"Bearer {token}")
    assert exc_info.value.status_code == 500
