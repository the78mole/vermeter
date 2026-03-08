"""OIDC token validation against a local Keycloak instance.

Flow:
  1. Keycloak signs access tokens with RS256 using its realm private key.
  2. The public keys are published at the JWKS endpoint:
       {KEYCLOAK_INTERNAL_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/certs
  3. This module fetches and caches those keys, then validates incoming
     Bearer tokens.  The 'iss' claim is checked by its suffix so that the
     browser-facing public URL (e.g. http://localhost:8081) and the
     backend-internal Docker URL (e.g. http://keycloak:8080) can differ.

Claims extracted:
  - sub           : Keycloak user ID (used as our user's primary key)
  - email         : user e-mail
  - name / given_name + family_name : display name
  - realm_access.roles : list of realm-level roles (e.g. ["tenant", "landlord"])
"""

from __future__ import annotations

import logging
import time
from typing import Any

import httpx
from jose import JWTError, jwt

from app.core.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# JWKS cache
# ---------------------------------------------------------------------------

_JWKS_CACHE: dict[str, Any] | None = None
_JWKS_CACHE_TS: float = 0.0
_JWKS_CACHE_TTL: float = 3600.0  # 1 hour


async def _fetch_jwks() -> dict[str, Any]:
    """Fetch the JWKS document from Keycloak, with a 1-hour in-memory cache."""
    global _JWKS_CACHE, _JWKS_CACHE_TS

    now = time.monotonic()
    if _JWKS_CACHE is not None and (now - _JWKS_CACHE_TS) < _JWKS_CACHE_TTL:
        return _JWKS_CACHE

    url = settings.keycloak_jwks_url
    logger.debug("Fetching JWKS from %s", url)
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        jwks = resp.json()

    _JWKS_CACHE = jwks
    _JWKS_CACHE_TS = now
    return jwks


def _invalidate_jwks_cache() -> None:
    """Force a re-fetch on the next validation (e.g. after key rotation)."""
    global _JWKS_CACHE_TS
    _JWKS_CACHE_TS = 0.0


# ---------------------------------------------------------------------------
# Token validation
# ---------------------------------------------------------------------------


class OIDCError(Exception):
    """Raised when token validation fails."""


async def validate_token(token: str) -> dict[str, Any]:
    """
    Validate a Keycloak-issued JWT access token and return its claims.

    Raises OIDCError on any validation failure so callers can map it to HTTP 401.
    """
    jwks = await _fetch_jwks()

    try:
        options: dict[str, Any] = {
            "verify_exp": True,
            "verify_aud": False,  # audience is flexible (account, frontend client, …)
            "verify_iss": False,  # issuer checked manually below (dev vs prod URL)
        }
        claims: dict[str, Any] = jwt.decode(
            token,
            jwks,
            algorithms=["RS256"],
            options=options,
        )
    except JWTError as exc:
        logger.debug("JWT decode error: %s", exc)
        # If the error might be due to stale JWKS (key rotation), retry once
        _invalidate_jwks_cache()
        try:
            jwks = await _fetch_jwks()
            claims = jwt.decode(token, jwks, algorithms=["RS256"], options=options)
        except JWTError as exc2:
            raise OIDCError(f"Invalid token: {exc2}") from exc2

    # Manual issuer suffix check (allows different public vs internal URLs)
    issuer: str = claims.get("iss", "")
    if settings.KEYCLOAK_VERIFY_ISS and not issuer.endswith(settings.keycloak_issuer_suffix):
        raise OIDCError(
            f"Token issuer '{issuer}' does not match expected realm "
            f"'{settings.keycloak_issuer_suffix}'"
        )

    return claims


# ---------------------------------------------------------------------------
# Claims helpers
# ---------------------------------------------------------------------------


def extract_user_info(claims: dict[str, Any]) -> dict[str, str]:
    """Extract display name, email and role from Keycloak token claims."""
    sub: str = claims.get("sub", "")
    email: str = claims.get("email", "")

    full_name: str = claims.get("name", "")
    if not full_name:
        given = claims.get("given_name", "")
        family = claims.get("family_name", "")
        full_name = f"{given} {family}".strip() or email

    realm_roles: list[str] = claims.get("realm_access", {}).get("roles", [])

    # Precedence: admin > landlord > tenant
    if "admin" in realm_roles:
        role = "ADMIN"
    elif "landlord" in realm_roles:
        role = "LANDLORD"
    elif "caretaker" in realm_roles:
        role = "CARETAKER"
    elif "tenant" in realm_roles:
        role = "TENANT"
    else:
        role = "TENANT"  # default to tenant for unknown roles

    return {
        "sub": sub,
        "email": email,
        "full_name": full_name,
        "role": role,
    }
