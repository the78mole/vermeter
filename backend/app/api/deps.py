"""FastAPI dependencies for authentication and authorisation.

Authentication is fully delegated to Keycloak (OIDC).  On each request the
Bearer token is validated against Keycloak's JWKS endpoint, and the user is
JIT-provisioned into our local DB on first login.

Row-Level Security (RLS) is enforced in individual route helpers by always
filtering queries on the authenticated user's ID.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.oidc import OIDCError, extract_user_info, validate_token
from app.models.models import AdminRole, User, UserRole

# Use HTTPBearer so the scheme name is "Bearer" (matches Keycloak tokens)
bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Validate the Keycloak Bearer token and return (or JIT-create) the local user.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        claims = await validate_token(credentials.credentials)
    except OIDCError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    info = extract_user_info(claims)
    keycloak_sub: str = info["sub"]

    # Look up by Keycloak sub (stored in User.id)
    result = await db.execute(select(User).where(User.id == keycloak_sub))
    user: User | None = result.scalar_one_or_none()

    if user is None:
        # JIT provisioning – create the user on first login
        user = User(
            id=keycloak_sub,
            email=info["email"],
            full_name=info["full_name"],
            hashed_password="",  # password is managed by Keycloak
            role=UserRole(info["role"]),
        )
        db.add(user)
        await db.flush()
        await db.refresh(user)
    else:
        # Sync name/email/role from Keycloak on every request
        updated = False
        if user.email != info["email"]:
            user.email = info["email"]
            updated = True
        if user.full_name != info["full_name"]:
            user.full_name = info["full_name"]
            updated = True
        new_role = UserRole(info["role"])
        if user.role != new_role:
            user.role = new_role
            updated = True
        if updated:
            await db.flush()

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User account is disabled")

    return user


async def require_landlord(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role not in (UserRole.LANDLORD, UserRole.ADMIN):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Landlord access required")
    return current_user


async def require_tenant(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role not in (UserRole.TENANT, UserRole.ADMIN):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant access required")
    return current_user


async def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Grants access to all admin sub-roles (SUPER_ADMIN, ADMIN, OPERATOR)."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current_user


async def require_admin_manager(current_user: User = Depends(get_current_user)) -> User:
    """Grants access to ADMIN and SUPER_ADMIN (can manage operators)."""
    if current_user.role != UserRole.ADMIN or current_user.admin_role not in (AdminRole.ADMIN, AdminRole.SUPER_ADMIN):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin or Super-Admin access required")
    return current_user


async def require_super_admin(current_user: User = Depends(get_current_user)) -> User:
    """Grants access to SUPER_ADMIN only."""
    if current_user.role != UserRole.ADMIN or current_user.admin_role != AdminRole.SUPER_ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Super-Admin access required")
    return current_user
