"""Auth routes.

Login / registration / password management are fully handled by Keycloak.
This router only exposes the /me endpoint which returns the current user's
profile from our local DB (JIT-provisioned on first request).
"""

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.models.models import User
from app.models.schemas import UserRead

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/me", response_model=UserRead)
async def read_me(current_user: User = Depends(get_current_user)) -> User:
    """Return the currently authenticated user's profile."""
    return current_user
