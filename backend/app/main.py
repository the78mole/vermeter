from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from app.api.v1 import api_router
from app.core.config import settings
from app.core.database import engine
from app.models.models import (  # noqa: F401 - ensure all models are imported before create_all
    CaretakerApartmentAssignment,
    CaretakerBuildingAssignment,
    BillLineItem,
    Contract,
    InterpolatedReading,
    LandlordDocument,
    LandlordProfile,
    Meter,
    MeterReading,
    Property,
    Unit,
    User,
    UtilityBill,
    VirtualMeterSource,
)
from app.core.database import Base


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Create tables on startup (in production, prefer Alembic migrations)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    # Ensure S3 bucket exists
    try:
        from app.services.storage import ensure_bucket
        await ensure_bucket()
    except Exception as exc:  # noqa: BLE001
        import logging
        logging.getLogger(__name__).warning("S3 bucket setup failed (non-fatal): %s", exc)
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
)

# CORS – allow the frontend origin in development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if not settings.is_production else ["https://localhost"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)

# Serve uploaded files
if os.path.exists(settings.UPLOAD_DIR):
    app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": settings.PROJECT_NAME}
