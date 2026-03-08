"""Tenant read-only routes – strict row-level security ensures tenants only see their own data."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, get_db
from app.models.models import (
    Contract,
    InterpolatedReading,
    Meter,
    MeterReading,
    Property,
    Unit,
    User,
    UtilityBill,
)
from app.models.schemas import (
    ContractRead,
    InterpolatedReadingRead,
    MeterRead,
    MeterReadingCreate,
    MeterReadingRead,
    UnitRead,
    UtilityBillRead,
)

router = APIRouter(prefix="/tenant", tags=["tenant"])


# ---------------------------------------------------------------------------
# Dashboard: active contract + unit info
# ---------------------------------------------------------------------------


@router.get("/contracts", response_model=list[ContractRead])
async def my_contracts(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Contract]:
    """All contracts belonging to the current tenant."""
    result = await db.execute(
        select(Contract).where(Contract.tenant_id == current_user.id)
    )
    return list(result.scalars().all())


@router.get("/contracts/{contract_id}", response_model=ContractRead)
async def get_my_contract(
    contract_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Contract:
    contract = await _get_tenant_contract(db, contract_id, current_user.id)
    return contract


@router.get("/contracts/{contract_id}/unit", response_model=UnitRead)
async def get_contract_unit(
    contract_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Unit:
    contract = await _get_tenant_contract(db, contract_id, current_user.id)
    result = await db.execute(select(Unit).where(Unit.id == contract.unit_id))
    unit = result.scalar_one_or_none()
    if not unit:
        raise HTTPException(status_code=404, detail="Unit not found")
    return unit


# ---------------------------------------------------------------------------
# Utility Bills (Nebenkostenabrechnungen)
# ---------------------------------------------------------------------------


@router.get("/utility-bills", response_model=list[UtilityBillRead])
async def my_utility_bills(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[UtilityBill]:
    result = await db.execute(
        select(UtilityBill)
        .options(selectinload(UtilityBill.line_items))
        .join(Contract, UtilityBill.contract_id == Contract.id)
        .where(Contract.tenant_id == current_user.id)
        .order_by(UtilityBill.billing_period_start.desc())
    )
    return list(result.scalars().all())


@router.get("/utility-bills/{bill_id}", response_model=UtilityBillRead)
async def get_my_utility_bill(
    bill_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UtilityBill:
    result = await db.execute(
        select(UtilityBill)
        .options(selectinload(UtilityBill.line_items))
        .join(Contract, UtilityBill.contract_id == Contract.id)
        .where(UtilityBill.id == bill_id, Contract.tenant_id == current_user.id)
    )
    bill = result.scalar_one_or_none()
    if not bill:
        raise HTTPException(status_code=404, detail="Utility bill not found")
    return bill


# ---------------------------------------------------------------------------
# Meter Readings – tenants can upload their own readings (Zählerstand einreichen)
# ---------------------------------------------------------------------------


@router.get("/meters", response_model=list[MeterRead])
async def my_meters(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Meter]:
    """Meters belonging to units the tenant has an active/recent contract for."""
    result = await db.execute(
        select(Meter)
        .join(Unit, Meter.unit_id == Unit.id)
        .join(Contract, Contract.unit_id == Unit.id)
        .where(Contract.tenant_id == current_user.id)
        .distinct()
    )
    return list(result.scalars().all())


@router.get("/meters/{meter_id}/readings", response_model=list[MeterReadingRead])
async def my_meter_readings(
    meter_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[MeterReading]:
    await _assert_tenant_meter_access(db, meter_id, current_user.id)
    result = await db.execute(
        select(MeterReading)
        .where(MeterReading.meter_id == meter_id)
        .order_by(MeterReading.reading_date)
    )
    return list(result.scalars().all())


@router.post("/meters/{meter_id}/readings", response_model=MeterReadingRead, status_code=status.HTTP_201_CREATED)
async def submit_meter_reading(
    meter_id: str,
    payload: MeterReadingCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MeterReading:
    """Tenants can submit their own meter readings (Zählerstand einreichen)."""
    await _assert_tenant_meter_access(db, meter_id, current_user.id)
    reading = MeterReading(**payload.model_dump(), meter_id=meter_id, uploaded_by_id=current_user.id)
    db.add(reading)
    await db.flush()
    await db.refresh(reading)
    return reading


# ---------------------------------------------------------------------------
# Interpolated readings for dashboard charts
# ---------------------------------------------------------------------------


@router.get("/meters/{meter_id}/interpolated", response_model=list[InterpolatedReadingRead])
async def my_interpolated_readings(
    meter_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[InterpolatedReading]:
    await _assert_tenant_meter_access(db, meter_id, current_user.id)
    result = await db.execute(
        select(InterpolatedReading)
        .where(InterpolatedReading.meter_id == meter_id)
        .order_by(InterpolatedReading.period_start)
    )
    return list(result.scalars().all())


# ---------------------------------------------------------------------------
# Helpers (strict RLS)
# ---------------------------------------------------------------------------


async def _get_tenant_contract(db: AsyncSession, contract_id: str, tenant_id: str) -> Contract:
    result = await db.execute(
        select(Contract).where(Contract.id == contract_id, Contract.tenant_id == tenant_id)
    )
    contract = result.scalar_one_or_none()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    return contract


async def _assert_tenant_meter_access(db: AsyncSession, meter_id: str, tenant_id: str) -> None:
    """Ensure tenant has a contract for the unit owning this meter."""
    result = await db.execute(
        select(Meter)
        .join(Unit, Meter.unit_id == Unit.id)
        .join(Contract, Contract.unit_id == Unit.id)
        .where(Meter.id == meter_id, Contract.tenant_id == tenant_id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Access to this meter is not allowed")
