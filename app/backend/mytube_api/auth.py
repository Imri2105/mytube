"""Cognito ID-token validation against the user pool's JWKS."""

import os
from functools import lru_cache
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

_bearer = HTTPBearer(auto_error=False)


@lru_cache
def _jwks_client() -> jwt.PyJWKClient:
    # PyJWKClient caches signing keys and refetches on an unknown kid.
    return jwt.PyJWKClient(f"{os.environ['COGNITO_ISSUER']}/.well-known/jwks.json")


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(401, detail, headers={"WWW-Authenticate": "Bearer"})


def current_user(creds: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)]) -> str:
    """Return the caller's Cognito `sub`, or raise 401."""
    if creds is None:
        raise _unauthorized("missing bearer token")
    token = creds.credentials
    try:
        key = _jwks_client().get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            key.key,
            algorithms=["RS256"],
            audience=os.environ["COGNITO_CLIENT_ID"],
            issuer=os.environ["COGNITO_ISSUER"],
            options={"require": ["exp", "iss", "aud", "sub"]},
        )
    except jwt.PyJWTError as exc:
        raise _unauthorized("invalid token") from exc
    if claims.get("token_use") != "id":
        raise _unauthorized("ID token required")
    return claims["sub"]


# Endpoint parameter type: `user: User` gives the caller's sub.
User = Annotated[str, Depends(current_user)]
