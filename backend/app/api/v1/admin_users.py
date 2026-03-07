"""Admin-User management routes.

Hierarchy:
- SUPER_ADMIN: can manage all admin users (super-admins, admins, operators)
- ADMIN: can manage operators (and update themselves)
- OPERATOR: read-only access to own profile; landlord management only

Route protection matrix:
  GET  /admin-users           → ADMIN, SUPER_ADMIN
  POST /admin-users           → SUPER_ADMIN (create any); ADMIN (create OPERATOR)
  GET  /admin-users/{id}      → ADMIN, SUPER_ADMIN (+ self)
  PATCH /admin-users/{id}     → SUPER_ADMIN (any); ADMIN (operators only)
  DELETE /admin-users/{id}    → SUPER_ADMIN only
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_current_user,
    get_db,
    require_admin_manager,
    require_super_admin,
)
from app.models.models import AdminRole, User, UserRole
from app.models.schemas import (
    AdminUserCreate,
    AdminUserProvisionResponse,
    AdminUserUpdate,
    UserRead,
)
from app.services.keycloak_admin import create_keycloak_user, delete_keycloak_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin-users", tags=["admin-users"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _can_manage(actor: User, target_role: AdminRole) -> bool:
    """Return True if *actor* is allowed to manage a user with *target_role*."""
    if actor.admin_role == AdminRole.SUPER_ADMIN:
        return True
    if actor.admin_role == AdminRole.ADMIN and target_role == AdminRole.OPERATOR:
        return True
    return False


# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------

@router.get("", response_model=list[UserRead])
async def list_admin_users(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin_manager),
) -> list[User]:
    """Return admin users visible to the caller.

    - SUPER_ADMIN sees everyone.
    - ADMIN sees only operators (and themselves).
    """
    stmt = select(User).where(User.role == UserRole.ADMIN)
    if current_user.admin_role == AdminRole.ADMIN:
        stmt = stmt.where(
            User.admin_role.in_([AdminRole.OPERATOR, AdminRole.ADMIN])
        )
    stmt = stmt.order_by(User.full_name)
    result = await db.execute(stmt)
    return list(result.scalars().all())


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------

@router.post("", response_model=AdminUserProvisionResponse, status_code=status.HTTP_201_CREATED)
async def create_admin_user(
    body: AdminUserCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin_manager),
) -> AdminUserProvisionResponse:
    """Provision a new admin user in Keycloak and the local DB."""
    if not _can_manage(current_user, body.admin_role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"You are not allowed to create users with role {body.admin_role}.",
        )

    # Check local email uniqueness
    existing = await db.scalar(select(User).where(User.email == body.email))
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="E-Mail ist bereits vergeben.")

    keycloak_created = False
    temp_password: str | None = None
    user_id: str | None = None

    try:
        user_id, temp_password = await create_keycloak_user(
            email=body.email,
            full_name=body.full_name,
            realm_role="admin",
        )
        keycloak_created = True
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    user = User(
        id=user_id,
        email=body.email,
        full_name=body.full_name,
        hashed_password="",
        role=UserRole.ADMIN,
        admin_role=body.admin_role,
    )
    db.add(user)
    try:
        await db.flush()
        await db.refresh(user)
    except Exception:
        if keycloak_created and user_id:
            await delete_keycloak_user(user_id)
        raise

    logger.info("Created admin user %s (%s) by %s", user.email, body.admin_role, current_user.email)

    result = AdminUserProvisionResponse.model_validate(user)
    result.keycloak_created = keycloak_created
    result.temp_password = temp_password
    return result


# ---------------------------------------------------------------------------
# Get single
# ---------------------------------------------------------------------------

@router.get("/me", response_model=UserRead)
async def get_own_profile(current_user: User = Depends(get_current_user)) -> User:
    """Return the calling admin user's own profile."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current_user


@router.get("/{user_id}", response_model=UserRead)
async def get_admin_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin_manager),
) -> User:
    user = await db.scalar(
        select(User).where(User.id == user_id, User.role == UserRole.ADMIN)
    )
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Admin user not found")
    if not _can_manage(current_user, user.admin_role):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return user


# ---------------------------------------------------------------------------
# Update
# ---------------------------------------------------------------------------

@router.patch("/{user_id}", response_model=UserRead)
async def update_admin_user(
    user_id: str,
    body: AdminUserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin_manager),
) -> User:
    user = await db.scalar(
        select(User).where(User.id == user_id, User.role == UserRole.ADMIN)
    )
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Admin user not found")
    if not _can_manage(current_user, user.admin_role):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    # Prevent self-demotion
    if user_id == current_user.id and body.admin_role is not None and body.admin_role != current_user.admin_role:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot change your own admin role")

    if body.full_name is not None:
        user.full_name = body.full_name
    if body.admin_role is not None:
        if not _can_manage(current_user, body.admin_role):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Cannot assign role {body.admin_role}")
        user.admin_role = body.admin_role
    if body.is_active is not None:
        user.is_active = body.is_active

    await db.flush()
    await db.refresh(user)
    return user


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_admin_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_super_admin),
) -> None:
    if user_id == current_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete yourself")
    user = await db.scalar(
        select(User).where(User.id == user_id, User.role == UserRole.ADMIN)
    )
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Admin user not found")

    await delete_keycloak_user(user_id)
    await db.delete(user)
    await db.flush()
    logger.info("Deleted admin user %s by %s", user.email, current_user.email)
