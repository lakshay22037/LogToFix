import os
from dataclasses import dataclass

import jwt
from fastapi import Header, HTTPException

# Supabase issues HS256 JWTs signed with the project's JWT secret (Project
# Settings -> API -> JWT Settings in the Supabase dashboard). Verified
# locally against the shared secret rather than a JWKS network call per
# request — see DECISIONS.md: "Authentication — Supabase Auth (Google
# OAuth), local JWT verification" for the scalability reasoning and the
# tradeoff against Supabase's newer asymmetric (RS256/JWKS) option.
SUPABASE_JWT_SECRET = os.environ.get("SUPABASE_JWT_SECRET")


@dataclass
class CurrentUser:
    id: str
    email: str


def get_current_user(authorization: str = Header(None)) -> CurrentUser:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    if not SUPABASE_JWT_SECRET:
        # Fail loudly rather than silently accepting unverifiable tokens —
        # a missing secret is a deployment misconfiguration, not something
        # to degrade gracefully past.
        raise HTTPException(status_code=500, detail="Server auth is not configured")

    token = authorization[len("Bearer "):]
    try:
        payload = jwt.decode(
            token,
            SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            audience="authenticated",
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired token") from exc

    return CurrentUser(id=payload["sub"], email=payload.get("email", ""))
