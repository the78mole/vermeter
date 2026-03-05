"""Landlord CRUD routes – full management of properties, units, contracts, meters, and billing."""

from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_db, require_landlord
from app.models.models import (
    Contract,
    ContractStatus,
    Meter,
    MeterReading,
    Property,
    Unit,
    User,
    UtilityBill,
    UtilityBillStatus,
)
from app.models.schemas import (
    ContractCreate,
    ContractRead,
    ContractStatusUpdate,
    ContractUpdate,
    MeterCreate,
    MeterRead,
    MeterReadingCreate,
    MeterReadingRead,
    PropertyCreate,
    PropertyRead,
    PropertyUpdate,
    UnitCreate,
    UnitRead,
    UnitUpdate,
    UserRead,
    UtilityBillRead,
    UtilityBillStatusUpdate,
)

router = APIRouter(prefix="/landlord", tags=["landlord"])


# ---------------------------------------------------------------------------
# Properties (Immobilien)
# ---------------------------------------------------------------------------


@router.get("/properties", response_model=list[PropertyRead])
async def list_properties(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_landlord),
) -> list[Property]:
    result = await db.execute(
        select(Property).where(Property.landlord_id == current_user.id)
    )
    return list(result.scalars().all())


@router.post("/properties", response_model=PropertyRead, status_code=status.HTTP_201_CREATED)
async def create_property(
    payload: PropertyCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_landlord),
) -> Property:
    prop = Property(**payload.model_dump(), landlord_id=current_user.id)
    db.add(prop)
    await db.flush()
    await db.refresh(prop)
    return prop


@router.get("/properties/{property_id}", response_model=PropertyRead)
async def get_property(
    property_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_landlord),
) -> Property:
    prop = await _get_owned_property(db, property_id, current_user.id)
    return prop


@router.patch("/properties/{property_id}", response_model=PropertyRead)
async def update_property(
    property_id: str,
    payload: PropertyUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_landlord),
) -> Property:
    prop = await _get_owned_property(db, property_id, current_user.id)
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(prop, field, value)
    await db.flush()
    await db.refresh(prop)
    return prop


@router.delete("/properties/{property_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_property(
    property_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_landlord),
) -> None:
    prop = await _get_owned_property(db, property_id, current_user.id)
    await db.delete(prop)


# ---------------------------------------------------------------------------
# Units (Mieteinheiten)
# ---------------------------------------------------------------------------


@router.get("/properties/{property_id}/units", response_model=list[UnitRead])
async def list_units(
    property_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_landlord),
) -> list[Unit]:
    await _get_owned_property(db, property_id, current_user.id)
    result = await db.execute(select(Unit).where(Unit.property_id == property_id))
    return list(result.scalars().all())


@router.post("/properties/{property_id}/units", response_model=UnitRead, status_code=status.HTTP_201_CREATED)
async def create_unit(
    property_id: str,
    payload: UnitCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_landlord),
) -> Unit:
    await _get_owned_property(db, property_id, current_user.id)
    unit = Unit(**payload.model_dump(), property_id=property_id)
    db.add(unit)
    await db.flush()
    await db.refresh(unit)
    return unit


@router.patch("/properties/{property_id}/units/{unit_id}", response_model=UnitRead)
async def update_unit(
    property_id: str,
    unit_id: str,
    payload: UnitUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_landlord),
) -> Unit:
    unit = await _get_owned_unit(db, unit_id, property_id, current_user.id)
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(unit, field, value)
    await db.flush()
    await db.refresh(unit)
    return unit


@router.delete("/properties/{property_id}/units/{unit_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_unit(
    property_id: str,
    unit_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_landlord),
) -> None:
    unit = await _get_owned_unit(db, unit_id, property_id, current_user.id)
    await db.delete(unit)


# ---------------------------------------------------------------------------
# Meters (Zähler)
# ---------------------------------------------------------------------------


@router.post("/units/{unit_id}/meters", response_model=MeterRead, status_code=status.HTTP_201_CREATED)
async def create_meter(
    unit_id: str,
    payload: MeterCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_landlord),
) -> Meter:
    await _assert_unit_ownership(db, unit_id, current_user.id)
    meter = Meter(**payload.model_dump(), unit_id=unit_id)
    db.add(meter)
    await db.flush()
    await db.refresh(meter)
    return meter


@router.get("/units/{unit_id}/meters", response_model=list[MeterRead])
async def list_meters(
    unit_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_landlord),
) -> list[Meter]:
    await _assert_unit_ownership(db, unit_id, current_user.id)
    result = await db.execute(select(Meter).where(Meter.unit_id == unit_id))
    return list(result.scalars().all())


@router.post("/meters/{meter_id}/readings", response_model=MeterReadingRead, status_code=status.HTTP_201_CREATED)
async def add_reading(
    meter_id: str,
    payload: MeterReadingCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_landlord),
) -> MeterReading:
    await _assert_meter_ownership(db, meter_id, current_user.id)
    reading = MeterReading(**payload.model_dump(), meter_id=meter_id, uploaded_by_id=current_user.id)
    db.add(reading)
    await db.flush()
    await db.refresh(reading)
    return reading


@router.get("/meters/{meter_id}/readings", response_model=list[MeterReadingRead])
async def list_readings(
    meter_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_landlord),
) -> list[MeterReading]:
    await _assert_meter_ownership(db, meter_id, current_user.id)
    result = await db.execute(
        select(MeterReading).where(MeterReading.meter_id == meter_id).order_by(MeterReading.reading_date)
    )
    return list(result.scalars().all())


# ---------------------------------------------------------------------------
# Contracts (Mietverträge)
# ---------------------------------------------------------------------------


@router.get("/contracts", response_model=list[ContractRead])
async def list_contracts(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_landlord),
) -> list[Contract]:
    result = await db.execute(
        select(Contract)
        .join(Unit, Contract.unit_id == Unit.id)
        .join(Property, Unit.property_id == Property.id)
        .where(Property.landlord_id == current_user.id)
    )
    return list(result.scalars().all())


@router.post("/contracts", response_model=ContractRead, status_code=status.HTTP_201_CREATED)
async def create_contract(
    payload: ContractCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_landlord),
) -> Contract:
    await _assert_unit_ownership(db, payload.unit_id, current_user.id)
    # Verify tenant exists
    tenant_result = await db.execute(select(User).where(User.id == payload.tenant_id))
    if not tenant_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Tenant not found")

    contract = Contract(**payload.model_dump())
    db.add(contract)
    await db.flush()
    await db.refresh(contract)
    return contract


@router.patch("/contracts/{contract_id}/status", response_model=ContractRead)
async def update_contract_status(
    contract_id: str,
    payload: ContractStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_landlord),
) -> Contract:
    contract = await _get_owned_contract(db, contract_id, current_user.id)
    _validate_contract_transition(contract.status, payload.status)
    contract.status = payload.status
    if payload.status == ContractStatus.ACTIVE:
        contract.signed_at = datetime.now(timezone.utc)
    elif payload.status == ContractStatus.TERMINATED:
        contract.terminated_at = datetime.now(timezone.utc)
    await db.flush()
    await db.refresh(contract)
    return contract


@router.patch("/contracts/{contract_id}", response_model=ContractRead)
async def update_contract(
    contract_id: str,
    payload: ContractUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_landlord),
) -> Contract:
    contract = await _get_owned_contract(db, contract_id, current_user.id)
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(contract, field, value)
    await db.flush()
    await db.refresh(contract)
    return contract


# ---------------------------------------------------------------------------
# Utility Bills (Nebenkostenabrechnungen)
# ---------------------------------------------------------------------------


@router.get("/utility-bills", response_model=list[UtilityBillRead])
async def list_utility_bills(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_landlord),
) -> list[UtilityBill]:
    result = await db.execute(
        select(UtilityBill)
        .options(selectinload(UtilityBill.line_items))
        .join(Contract, UtilityBill.contract_id == Contract.id)
        .join(Unit, Contract.unit_id == Unit.id)
        .join(Property, Unit.property_id == Property.id)
        .where(Property.landlord_id == current_user.id)
    )
    return list(result.scalars().all())


@router.patch("/utility-bills/{bill_id}/status", response_model=UtilityBillRead)
async def update_bill_status(
    bill_id: str,
    payload: UtilityBillStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_landlord),
) -> UtilityBill:
    bill = await _get_owned_bill(db, bill_id, current_user.id)
    _validate_bill_transition(bill.status, payload.status)
    bill.status = payload.status
    now = datetime.now(timezone.utc)
    if payload.status == UtilityBillStatus.SENT_TO_TENANT:
        bill.sent_at = now
    elif payload.status == UtilityBillStatus.PAID:
        bill.paid_at = now
    elif payload.status == UtilityBillStatus.DISPUTED:
        bill.disputed_at = now
    await db.flush()
    result = await db.execute(
        select(UtilityBill).options(selectinload(UtilityBill.line_items)).where(UtilityBill.id == bill_id)
    )
    return result.scalar_one()


# ---------------------------------------------------------------------------
# Tenants overview
# ---------------------------------------------------------------------------


@router.get("/tenants", response_model=list[UserRead])
async def list_tenants(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_landlord),
) -> list[User]:
    """Return all tenants that have/had a contract in any of this landlord's units."""
    result = await db.execute(
        select(User)
        .join(Contract, Contract.tenant_id == User.id)
        .join(Unit, Contract.unit_id == Unit.id)
        .join(Property, Unit.property_id == Property.id)
        .where(Property.landlord_id == current_user.id)
        .distinct()
    )
    return list(result.scalars().all())


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


async def _get_owned_property(db: AsyncSession, property_id: str, landlord_id: str) -> Property:
    result = await db.execute(
        select(Property).where(Property.id == property_id, Property.landlord_id == landlord_id)
    )
    prop = result.scalar_one_or_none()
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    return prop


async def _get_owned_unit(db: AsyncSession, unit_id: str, property_id: str, landlord_id: str) -> Unit:
    result = await db.execute(
        select(Unit)
        .join(Property, Unit.property_id == Property.id)
        .where(Unit.id == unit_id, Unit.property_id == property_id, Property.landlord_id == landlord_id)
    )
    unit = result.scalar_one_or_none()
    if not unit:
        raise HTTPException(status_code=404, detail="Unit not found")
    return unit


async def _assert_unit_ownership(db: AsyncSession, unit_id: str, landlord_id: str) -> Unit:
    result = await db.execute(
        select(Unit)
        .join(Property, Unit.property_id == Property.id)
        .where(Unit.id == unit_id, Property.landlord_id == landlord_id)
    )
    unit = result.scalar_one_or_none()
    if not unit:
        raise HTTPException(status_code=404, detail="Unit not found or access denied")
    return unit


async def _assert_meter_ownership(db: AsyncSession, meter_id: str, landlord_id: str) -> Meter:
    result = await db.execute(
        select(Meter)
        .join(Unit, Meter.unit_id == Unit.id)
        .join(Property, Unit.property_id == Property.id)
        .where(Meter.id == meter_id, Property.landlord_id == landlord_id)
    )
    meter = result.scalar_one_or_none()
    if not meter:
        raise HTTPException(status_code=404, detail="Meter not found or access denied")
    return meter


async def _get_owned_contract(db: AsyncSession, contract_id: str, landlord_id: str) -> Contract:
    result = await db.execute(
        select(Contract)
        .join(Unit, Contract.unit_id == Unit.id)
        .join(Property, Unit.property_id == Property.id)
        .where(Contract.id == contract_id, Property.landlord_id == landlord_id)
    )
    contract = result.scalar_one_or_none()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found or access denied")
    return contract


async def _get_owned_bill(db: AsyncSession, bill_id: str, landlord_id: str) -> UtilityBill:
    result = await db.execute(
        select(UtilityBill)
        .join(Contract, UtilityBill.contract_id == Contract.id)
        .join(Unit, Contract.unit_id == Unit.id)
        .join(Property, Unit.property_id == Property.id)
        .where(UtilityBill.id == bill_id, Property.landlord_id == landlord_id)
    )
    bill = result.scalar_one_or_none()
    if not bill:
        raise HTTPException(status_code=404, detail="Utility bill not found or access denied")
    return bill


_CONTRACT_TRANSITIONS: dict[ContractStatus, set[ContractStatus]] = {
    ContractStatus.DRAFT: {ContractStatus.PENDING_SIGNATURE},
    ContractStatus.PENDING_SIGNATURE: {ContractStatus.ACTIVE, ContractStatus.DRAFT},
    ContractStatus.ACTIVE: {ContractStatus.TERMINATED},
    ContractStatus.TERMINATED: {ContractStatus.ARCHIVED},
    ContractStatus.ARCHIVED: set(),
}

_BILL_TRANSITIONS: dict[UtilityBillStatus, set[UtilityBillStatus]] = {
    UtilityBillStatus.CALCULATING: {UtilityBillStatus.REVIEW_REQUIRED},
    UtilityBillStatus.REVIEW_REQUIRED: {UtilityBillStatus.SENT_TO_TENANT, UtilityBillStatus.CALCULATING},
    UtilityBillStatus.SENT_TO_TENANT: {UtilityBillStatus.PAID, UtilityBillStatus.DISPUTED},
    UtilityBillStatus.PAID: set(),
    UtilityBillStatus.DISPUTED: {UtilityBillStatus.REVIEW_REQUIRED, UtilityBillStatus.PAID},
}


def _validate_contract_transition(current: ContractStatus, new: ContractStatus) -> None:
    if new not in _CONTRACT_TRANSITIONS.get(current, set()):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid contract status transition: {current} -> {new}",
        )


def _validate_bill_transition(current: UtilityBillStatus, new: UtilityBillStatus) -> None:
    if new not in _BILL_TRANSITIONS.get(current, set()):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid bill status transition: {current} -> {new}",
        )
