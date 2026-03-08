"""Admin routes – platform admin manages landlord accounts.

Only users with role=ADMIN can access these endpoints.
Creating a landlord now also provisions a Keycloak account via the
rental-backend service account (client_credentials grant).  The generated
temporary password is returned once and never stored.
"""

from __future__ import annotations

import logging
import uuid

import httpx
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_db, require_admin, require_admin_manager
from app.models.models import LandlordDocument, LandlordProfile, Tag, User, UserRole
from app.models.schemas import (
    CaretakerCreate,
    CaretakerProvisionResponse,
    LandlordCreate,
    LandlordDocumentRead,
    LandlordDocumentUpdate,
    LandlordProfileRead,
    LandlordProfileUpsert,
    LandlordProvisionResponse,
    LandlordUpdate,
    LandlordWithProfile,
    TagRead,
    UserRead,
)
from app.services.keycloak_admin import create_keycloak_user, delete_keycloak_user
from app.services.storage import delete_object, download_object, upload_object

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/landlords", response_model=list[LandlordWithProfile])
async def list_landlords(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
) -> list[User]:
    """Return all users with role LANDLORD, including their profile data."""
    result = await db.execute(
        select(User)
        .where(User.role == UserRole.LANDLORD)
        .options(selectinload(User.landlord_profile))
        .order_by(User.created_at)
    )
    return list(result.scalars().all())


@router.post(
    "/landlords",
    response_model=LandlordProvisionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_landlord(
    body: LandlordCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
) -> LandlordProvisionResponse:
    """Create a new landlord – both in the local DB *and* in Keycloak.

    The response contains a one-time **temporary password** that the landlord
    must change on their first login.  It is never stored server-side.

    If the Keycloak account cannot be created (e.g. service unavailable), the
    DB record is still persisted so the admin can retry or create the Keycloak
    account manually.  ``keycloak_created`` in the response signals success.
    """
    # ── 1. Guard against duplicate emails in the local DB ─────────────────────
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A user with email '{body.email}' already exists.",
        )

    # ── 2. Create the Keycloak account first ───────────────────────────────────
    keycloak_id: str | None = None
    temp_password: str | None = None
    keycloak_created = False

    try:
        keycloak_id, temp_password = await create_keycloak_user(body.email, body.full_name)
        keycloak_created = True
    except ValueError as exc:
        # email already exists in Keycloak → surface as 409
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except (httpx.HTTPError, httpx.TimeoutException) as exc:
        # Keycloak unreachable – create DB record anyway, admin can retry
        logger.warning("Keycloak account creation failed for %s: %s", body.email, exc)

    # ── 3. Persist the DB record ───────────────────────────────────────────────
    user = User(
        id=str(uuid.uuid4()),
        email=body.email,
        full_name=body.full_name,
        hashed_password="",  # identity managed by Keycloak
        role=UserRole.LANDLORD,
        is_active=True,
    )
    db.add(user)
    try:
        await db.flush()
        await db.refresh(user)
    except Exception:
        # DB failure – remove the Keycloak user to keep systems consistent
        if keycloak_id:
            await delete_keycloak_user(keycloak_id)
        raise

    # ── 4. Build response (temp_password is returned exactly once) ─────────────
    return LandlordProvisionResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at,
        keycloak_created=keycloak_created,
        temp_password=temp_password,
    )


@router.get("/caretakers", response_model=list[UserRead])
async def list_caretakers(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
) -> list[User]:
    result = await db.execute(
        select(User)
        .where(User.role == UserRole.CARETAKER)
        .order_by(User.created_at)
    )
    return list(result.scalars().all())


@router.post(
    "/caretakers",
    response_model=CaretakerProvisionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_caretaker(
    body: CaretakerCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
) -> CaretakerProvisionResponse:
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A user with email '{body.email}' already exists.",
        )

    keycloak_id: str | None = None
    temp_password: str | None = None
    keycloak_created = False

    try:
        keycloak_id, temp_password = await create_keycloak_user(body.email, body.full_name, realm_role="caretaker")
        keycloak_created = True
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except (httpx.HTTPError, httpx.TimeoutException) as exc:
        logger.warning("Keycloak account creation failed for %s: %s", body.email, exc)

    user = User(
        id=str(uuid.uuid4()),
        email=body.email,
        full_name=body.full_name,
        hashed_password="",
        role=UserRole.CARETAKER,
        is_active=True,
    )
    db.add(user)
    try:
        await db.flush()
        await db.refresh(user)
    except Exception:
        if keycloak_id:
            await delete_keycloak_user(keycloak_id)
        raise

    return CaretakerProvisionResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at,
        keycloak_created=keycloak_created,
        temp_password=temp_password,
    )


@router.patch("/landlords/{landlord_id}", response_model=UserRead)
async def update_landlord(
    landlord_id: str,
    body: LandlordUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
) -> User:
    """Update a landlord's name or active status."""
    result = await db.execute(
        select(User).where(User.id == landlord_id, User.role == UserRole.LANDLORD)
    )
    user: User | None = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Landlord not found")

    if body.full_name is not None:
        user.full_name = body.full_name
    if body.is_active is not None:
        user.is_active = body.is_active

    await db.flush()
    await db.refresh(user)
    return user


@router.delete("/landlords/{landlord_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_landlord(
    landlord_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
) -> None:
    """Deactivate a landlord account (soft-delete: sets is_active=False)."""
    result = await db.execute(
        select(User).where(User.id == landlord_id, User.role == UserRole.LANDLORD)
    )
    user: User | None = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Landlord not found")

    user.is_active = False
    await db.flush()


@router.get("/landlords/{landlord_id}/profile", response_model=LandlordProfileRead)
async def get_landlord_profile(
    landlord_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
) -> LandlordProfile:
    """Return the profile for a landlord (creates an empty one if not yet present)."""
    result = await db.execute(
        select(LandlordProfile).where(LandlordProfile.user_id == landlord_id)
    )
    profile = result.scalar_one_or_none()
    if profile is None:
        # Auto-create on first access
        profile = LandlordProfile(id=str(uuid.uuid4()), user_id=landlord_id)
        db.add(profile)
        await db.flush()
        await db.refresh(profile)
    return profile


@router.put("/landlords/{landlord_id}/profile", response_model=LandlordProfileRead)
async def upsert_landlord_profile(
    landlord_id: str,
    body: LandlordProfileUpsert,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
) -> LandlordProfile:
    """Create or update the profile for a landlord (upsert semantics)."""
    # Make sure the landlord exists
    landlord = await db.scalar(
        select(User).where(User.id == landlord_id, User.role == UserRole.LANDLORD)
    )
    if landlord is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Landlord not found")

    result = await db.execute(
        select(LandlordProfile).where(LandlordProfile.user_id == landlord_id)
    )
    profile = result.scalar_one_or_none()
    if profile is None:
        profile = LandlordProfile(id=str(uuid.uuid4()), user_id=landlord_id)
        db.add(profile)

    for field, value in body.model_dump(exclude_unset=False).items():
        setattr(profile, field, value)

    await db.flush()
    await db.refresh(profile)
    return profile


@router.get("/landlords/{landlord_id}/documents", response_model=list[LandlordDocumentRead])
async def list_documents(
    landlord_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
) -> list[LandlordDocument]:
    """List all documents for a landlord."""
    result = await db.execute(
        select(LandlordDocument)
        .where(LandlordDocument.landlord_id == landlord_id)
        .options(selectinload(LandlordDocument.tags))
        .order_by(LandlordDocument.uploaded_at.desc())
    )
    return list(result.scalars().all())


@router.post(
    "/landlords/{landlord_id}/documents",
    response_model=LandlordDocumentRead,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    landlord_id: str,
    file: UploadFile = File(...),
    description: str | None = Query(None, max_length=512),
    tags: list[str] = Query(default=[]),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
) -> LandlordDocument:
    """Upload a document and store it in S3."""
    # Verify landlord exists
    landlord = await db.scalar(
        select(User).where(User.id == landlord_id, User.role == UserRole.LANDLORD)
    )
    if landlord is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Landlord not found")

    data = await file.read()
    doc_id = str(uuid.uuid4())
    # Sanitise filename to prevent path traversal
    safe_name = (file.filename or "file").replace("/", "_").replace("\\", "_")
    s3_key = f"landlords/{landlord_id}/{doc_id}/{safe_name}"

    await upload_object(s3_key, data, file.content_type or "application/octet-stream")

    # Get-or-create tags
    tag_objects: list[Tag] = []
    for raw in tags:
        name = raw.strip()
        if not name:
            continue
        tag_obj = await db.scalar(select(Tag).where(Tag.name == name))
        if tag_obj is None:
            tag_obj = Tag(name=name)
            db.add(tag_obj)
            await db.flush()
        tag_objects.append(tag_obj)

    doc = LandlordDocument(
        id=doc_id,
        landlord_id=landlord_id,
        filename=safe_name,
        content_type=file.content_type or "application/octet-stream",
        size_bytes=len(data),
        description=description,
        s3_key=s3_key,
        tags=tag_objects,
    )
    db.add(doc)
    await db.flush()
    # Reload with tags explicitly
    doc = await db.scalar(
        select(LandlordDocument)
        .options(selectinload(LandlordDocument.tags))
        .where(LandlordDocument.id == doc_id)
    )
    return doc


@router.get("/landlords/{landlord_id}/documents/{doc_id}/download")
async def download_document(
    landlord_id: str,
    doc_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
) -> Response:
    """Download a document – streams the file from S3 through the backend."""
    result = await db.execute(
        select(LandlordDocument).where(
            LandlordDocument.id == doc_id,
            LandlordDocument.landlord_id == landlord_id,
        )
    )
    doc: LandlordDocument | None = result.scalar_one_or_none()
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    data = await download_object(doc.s3_key)
    return Response(
        content=data,
        media_type=doc.content_type,
        headers={"Content-Disposition": f'attachment; filename="{doc.filename}"'},
    )


@router.patch("/landlords/{landlord_id}/documents/{doc_id}", response_model=LandlordDocumentRead)
async def update_document(
    landlord_id: str,
    doc_id: str,
    body: LandlordDocumentUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
) -> LandlordDocument:
    """Update tags and/or description of an existing document."""
    result = await db.execute(
        select(LandlordDocument)
        .where(LandlordDocument.id == doc_id, LandlordDocument.landlord_id == landlord_id)
        .options(selectinload(LandlordDocument.tags))
    )
    doc: LandlordDocument | None = result.scalar_one_or_none()
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    # Update description
    if body.description is not None:
        doc.description = body.description
    else:
        doc.description = None

    # Replace tags
    tag_objects: list[Tag] = []
    for raw in body.tags:
        name = raw.strip().lower()[:100]
        if not name:
            continue
        tag_obj = await db.scalar(select(Tag).where(Tag.name == name))
        if tag_obj is None:
            tag_obj = Tag(name=name)
            db.add(tag_obj)
            await db.flush()
        tag_objects.append(tag_obj)
    doc.tags = tag_objects

    await db.flush()
    await db.refresh(doc)
    # Reload tags
    result2 = await db.execute(
        select(LandlordDocument)
        .where(LandlordDocument.id == doc_id)
        .options(selectinload(LandlordDocument.tags))
    )
    return result2.scalar_one()


@router.patch("/landlords/{landlord_id}/documents/{doc_id}", response_model=LandlordDocumentRead)
async def update_document(
    landlord_id: str,
    doc_id: str,
    body: LandlordDocumentUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
) -> LandlordDocument:
    """Update tags and/or description of an existing document."""
    result = await db.execute(
        select(LandlordDocument)
        .where(LandlordDocument.id == doc_id, LandlordDocument.landlord_id == landlord_id)
        .options(selectinload(LandlordDocument.tags))
    )
    doc: LandlordDocument | None = result.scalar_one_or_none()
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    doc.description = body.description

    # Replace tags
    tag_objects: list[Tag] = []
    for raw in body.tags:
        name = raw.strip().lower()[:100]
        if not name:
            continue
        tag_obj = await db.scalar(select(Tag).where(Tag.name == name))
        if tag_obj is None:
            tag_obj = Tag(name=name)
            db.add(tag_obj)
            await db.flush()
        tag_objects.append(tag_obj)
    doc.tags = tag_objects

    await db.flush()
    result2 = await db.execute(
        select(LandlordDocument)
        .where(LandlordDocument.id == doc_id)
        .options(selectinload(LandlordDocument.tags))
    )
    return result2.scalar_one()


@router.delete("/landlords/{landlord_id}/documents/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    landlord_id: str,
    doc_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
) -> None:
    """Delete a document from S3 and the database."""
    result = await db.execute(
        select(LandlordDocument).where(
            LandlordDocument.id == doc_id,
            LandlordDocument.landlord_id == landlord_id,
        )
    )
    doc: LandlordDocument | None = result.scalar_one_or_none()
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    await delete_object(doc.s3_key)
    await db.delete(doc)
    await db.flush()


@router.get("/tags", response_model=list[TagRead])
async def search_tags(
    q: str = Query("", max_length=100),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
) -> list[Tag]:
    """Return all tags matching the search query (for autocomplete)."""
    stmt = select(Tag).order_by(Tag.name).limit(30)
    if q.strip():
        stmt = stmt.where(Tag.name.ilike(f"%{q.strip()}%"))
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.get("/stats", response_model=dict)
async def get_stats(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin_manager),
) -> dict:
    """Return platform-wide statistics."""
    from app.models.models import Contract, Property
    from sqlalchemy import func

    landlord_count = await db.scalar(
        select(func.count()).where(User.role == UserRole.LANDLORD)
    )
    active_landlord_count = await db.scalar(
        select(func.count()).where(User.role == UserRole.LANDLORD, User.is_active == True)  # noqa: E712
    )
    tenant_count = await db.scalar(
        select(func.count()).where(User.role == UserRole.TENANT)
    )
    property_count = await db.scalar(select(func.count()).select_from(Property))
    contract_count = await db.scalar(select(func.count()).select_from(Contract))

    return {
        "landlords_total": landlord_count or 0,
        "landlords_active": active_landlord_count or 0,
        "tenants_total": tenant_count or 0,
        "properties_total": property_count or 0,
        "contracts_total": contract_count or 0,
    }
