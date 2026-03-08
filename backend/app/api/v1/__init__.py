from fastapi import APIRouter

from app.api.v1 import admin, admin_users, auth, billing, landlord, tenant

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(admin.router)
api_router.include_router(admin_users.router)
api_router.include_router(landlord.router)
api_router.include_router(tenant.router)
api_router.include_router(billing.router)
