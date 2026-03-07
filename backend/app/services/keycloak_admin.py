"""Keycloak Admin API client.

Uses the ``rental-backend`` service account (client_credentials grant) to
obtain short-lived admin tokens and call the Keycloak Admin REST API.

All operations are async and rely on the ``httpx`` async client that is
already a project dependency.
"""

from __future__ import annotations

import logging
import secrets
import string

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

# ── URL helpers ───────────────────────────────────────────────────────────────

def _token_url() -> str:
    return (
        f"{settings.KEYCLOAK_INTERNAL_URL}"
        f"/realms/{settings.KEYCLOAK_REALM}"
        "/protocol/openid-connect/token"
    )


def _admin_base() -> str:
    return (
        f"{settings.KEYCLOAK_INTERNAL_URL}"
        f"/admin/realms/{settings.KEYCLOAK_REALM}"
    )


# ── Internal helpers ──────────────────────────────────────────────────────────

async def _service_account_token() -> str:
    """Exchange client credentials for an access token."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            _token_url(),
            data={
                "grant_type": "client_credentials",
                "client_id": settings.KEYCLOAK_ADMIN_CLIENT_ID,
                "client_secret": settings.KEYCLOAK_ADMIN_CLIENT_SECRET,
            },
        )
        resp.raise_for_status()
        return resp.json()["access_token"]


def _generate_temp_password(length: int = 16) -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%&"
    return "".join(secrets.choice(alphabet) for _ in range(length))


# ── Public API ────────────────────────────────────────────────────────────────

async def create_keycloak_user(email: str, full_name: str, realm_role: str = "landlord") -> tuple[str, str]:
    """Create a Keycloak user and assign *realm_role*.

    Returns ``(keycloak_user_id, temp_password)``.

    Raises:
        ValueError: if an account with *email* already exists in Keycloak.
        httpx.HTTPStatusError: for other Keycloak API errors.
    """
    token = await _service_account_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    given, _, family = full_name.partition(" ")

    async with httpx.AsyncClient() as http:
        # 1 – Create the user record
        resp = await http.post(
            f"{_admin_base()}/users",
            json={
                "username": email,
                "email": email,
                "emailVerified": True,
                "enabled": True,
                "firstName": given,
                "lastName": family or given,
                "requiredActions": ["UPDATE_PASSWORD"],
            },
            headers=headers,
        )
        if resp.status_code == 409:
            raise ValueError(
                f"Keycloak: A user with email '{email}' already exists."
            )
        resp.raise_for_status()

        # 2 – Extract the new user's UUID from the Location header
        location = resp.headers.get("Location", "")
        user_id = location.rsplit("/", 1)[-1]

        # 3 – Set a temporary password (user must change on first login)
        temp_pw = _generate_temp_password()
        pw_resp = await http.put(
            f"{_admin_base()}/users/{user_id}/reset-password",
            json={"type": "password", "value": temp_pw, "temporary": True},
            headers=headers,
        )
        pw_resp.raise_for_status()

        # 4 – Assign the realm role
        roles_resp = await http.get(f"{_admin_base()}/roles", headers=headers)
        roles_resp.raise_for_status()
        target_role = next(
            (r for r in roles_resp.json() if r["name"] == realm_role),
            None,
        )
        if target_role:
            await http.post(
                f"{_admin_base()}/users/{user_id}/role-mappings/realm",
                json=[target_role],
                headers=headers,
            )
        else:
            logger.warning(
                "Keycloak realm role '%s' not found – skipping role assignment.", realm_role
            )

    logger.info("Created Keycloak user %s for email %s", user_id, email)
    return user_id, temp_pw


async def delete_keycloak_user(keycloak_id: str) -> None:
    """Delete a Keycloak user by UUID (used for DB rollback compensation)."""
    try:
        token = await _service_account_token()
        headers = {"Authorization": f"Bearer {token}"}
        async with httpx.AsyncClient() as http:
            resp = await http.delete(
                f"{_admin_base()}/users/{keycloak_id}",
                headers=headers,
            )
            if resp.status_code not in (204, 404):
                resp.raise_for_status()
    except Exception:  # noqa: BLE001
        logger.warning("Failed to delete Keycloak user %s during rollback.", keycloak_id)
