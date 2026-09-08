import os
from dataclasses import dataclass

import jwt
from fastapi import Header, HTTPException
from jwt import PyJWKClient

# Newer Supabase projects sign JWTs with a rotating asymmetric key (ES256)
# instead of a shared HS256 secret, publishing the public keys at a JWKS
# endpoint. We verify against that — no shared secret to protect, and
# PyJWKClient caches keys internally so this isn't a network call on every
# request. See DECISIONS.md: "Authentication — Supabase Auth" (the JWKS
# correction) for why this replaced the original shared-secret design.
SUPABASE_URL = os.environ.get("SUPABASE_URL")
_JWKS_CLIENT = PyJWKClient(f"{SUPABASE_URL}/auth/v1/.well-known/jwks.json") if SUPABASE_URL else None


@dataclass
class CurrentUser:
    id: str
    email: str


def get_current_user(authorization: str = Header(None)) -> CurrentUser:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    if _JWKS_CLIENT is None:
        # Fail loudly rather than silently accepting unverifiable tokens —
        # a missing SUPABASE_URL is a deployment misconfiguration, not
        # something to degrade gracefully past.
        raise HTTPException(status_code=500, detail="Server auth is not configured")

    token = authorization[len("Bearer "):]
    try:
        signing_key = _JWKS_CLIENT.get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["ES256", "RS256"],
            audience="authenticated",
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired token") from exc

    return CurrentUser(id=payload["sub"], email=payload.get("email", ""))
