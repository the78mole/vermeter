"""Landlord CRUD routes – full management of properties, units, contracts, meters, and billing."""

from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_db, require_landlord, require_landlord_or_caretaker
from app.models.models import (
    CaretakerApartmentAssignment,
    CaretakerBuildingAssignment,
    Contract,
    ContractStatus,
    Meter,
    MeterReading,
    Property,
    Unit,
    User,
    UserRole,
    UtilityBill,
    UtilityBillStatus,
)
from app.models.schemas import (
    ApartmentCreate,
    ApartmentRead,
    ApartmentUpdate,
    BuildingCreate,
    BuildingRead,
    BuildingUpdate,
    CaretakerAssignmentRead,
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


@router.get("/buildings", response_model=list[BuildingRead])
async def list_buildings(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_landlord_or_caretaker),
) -> list[Property]:
    result = await db.execute(_property_visibility_stmt(current_user))
    return list(result.scalars().all())


@router.post("/buildings", response_model=BuildingRead, status_code=status.HTTP_201_CREATED)
async def create_building(
    payload: BuildingCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_landlord_or_caretaker),
) -> Property:
    _ensure_landlord_or_admin(current_user)
    building = Property(**payload.model_dump(), landlord_id=current_user.id)
    db.add(building)
    await db.flush()
    await db.refresh(building)
    return building


@router.patch("/buildings/{building_id}", response_model=BuildingRead)
async def update_building(
    building_id: str,
    payload: BuildingUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_landlord_or_caretaker),
) -> Property:
    _ensure_landlord_or_admin(current_user)
    building = await _get_accessible_property(db, building_id, current_user)
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(building, field, value)
    await db.flush()
    await db.refresh(building)
    return building


@router.get("/buildings/{building_id}/apartments", response_model=list[ApartmentRead])
async def list_apartments(
    building_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_landlord_or_caretaker),
) -> list[Unit]:
    await _get_accessible_property(db, building_id, current_user)
    result = await db.execute(select(Unit).where(Unit.property_id == building_id).order_by(Unit.name))
    return list(result.scalars().all())


@router.post("/buildings/{building_id}/apartments", response_model=ApartmentRead, status_code=status.HTTP_201_CREATED)
async def create_apartment(
    building_id: str,
    payload: ApartmentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_landlord_or_caretaker),
) -> Unit:
    _ensure_landlord_or_admin(current_user)
    await _get_accessible_property(db, building_id, current_user)
    apartment = Unit(**payload.model_dump(), property_id=building_id)
    db.add(apartment)
    await db.flush()
    await db.refresh(apartment)
    return apartment


@router.post("/buildings/{building_id}/caretakers/{caretaker_id}", response_model=CaretakerAssignmentRead, status_code=status.HTTP_201_CREATED)
async def assign_caretaker_to_building(
    building_id: str,
    caretaker_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_landlord),
) -> CaretakerBuildingAssignment:
    await _get_accessible_property(db, building_id, current_user)
    await _assert_caretaker_exists(db, caretaker_id)
    existing = await db.scalar(
        select(CaretakerBuildingAssignment).where(
            CaretakerBuildingAssignment.caretaker_id == caretaker_id,
            CaretakerBuildingAssignment.building_id == building_id,
        )
    )
    if existing:
        return existing
    assignment = CaretakerBuildingAssignment(caretaker_id=caretaker_id, building_id=building_id)
    db.add(assignment)
    await db.flush()
    await db.refresh(assignment)
    return assignment


@router.delete("/buildings/{building_id}/caretakers/{caretaker_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unassign_caretaker_from_building(
    building_id: str,
    caretaker_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_landlord),
) -> None:
    await _get_accessible_property(db, building_id, current_user)
    assignment = await db.scalar(
        select(CaretakerBuildingAssignment).where(
            CaretakerBuildingAssignment.caretaker_id == caretaker_id,
            CaretakerBuildingAssignment.building_id == building_id,
        )
    )
    if assignment:
        await db.delete(assignment)


@router.post("/apartments/{apartment_id}/caretakers/{caretaker_id}", response_model=CaretakerAssignmentRead, status_code=status.HTTP_201_CREATED)
async def assign_caretaker_to_apartment(
    apartment_id: str,
    caretaker_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_landlord),
) -> CaretakerApartmentAssignment:
    apartment = await _assert_unit_access(db, apartment_id, current_user)
    await _assert_caretaker_exists(db, caretaker_id)
    existing = await db.scalar(
        select(CaretakerApartmentAssignment).where(
            CaretakerApartmentAssignment.caretaker_id == caretaker_id,
            CaretakerApartmentAssignment.apartment_id == apartment.id,
        )
    )
    if existing:
        return existing
    assignment = CaretakerApartmentAssignment(caretaker_id=caretaker_id, apartment_id=apartment.id)
    db.add(assignment)
    await db.flush()
    await db.refresh(assignment)
    return assignment


@router.delete("/apartments/{apartment_id}/caretakers/{caretaker_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unassign_caretaker_from_apartment(
    apartment_id: str,
    caretaker_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_landlord),
) -> None:
    await _assert_unit_access(db, apartment_id, current_user)
    assignment = await db.scalar(
        select(CaretakerApartmentAssignment).where(
            CaretakerApartmentAssignment.caretaker_id == caretaker_id,
            CaretakerApartmentAssignment.apartment_id == apartment_id,
        )
    )
    if assignment:
        await db.delete(assignment)


# ---------------------------------------------------------------------------
# Properties (Immobilien)
# ---------------------------------------------------------------------------


@router.get("/properties", response_model=list[PropertyRead])
async def list_properties(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_landlord_or_caretaker),
) -> list[Property]:
    result = await db.execute(_property_visibility_stmt(current_user))
    return list(result.scalars().all())


@router.post("/properties", response_model=PropertyRead, status_code=status.HTTP_201_CREATED)
async def create_property(
    payload: PropertyCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_landlord_or_caretaker),
) -> Property:
    _ensure_landlord_or_admin(current_user)
    prop = Property(**payload.model_dump(), landlord_id=current_user.id)
    db.add(prop)
    await db.flush()
    await db.refresh(prop)
    return prop


@router.get("/properties/{property_id}", response_model=PropertyRead)
async def get_property(
    property_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_landlord_or_caretaker),
) -> Property:
    prop = await _get_accessible_property(db, property_id, current_user)
    return prop


@router.patch("/properties/{property_id}", response_model=PropertyRead)
async def update_property(
    property_id: str,
    payload: PropertyUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_landlord_or_caretaker),
) -> Property:
    _ensure_landlord_or_admin(current_user)
    prop = await _get_accessible_property(db, property_id, current_user)
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(prop, field, value)
    await db.flush()
    await db.refresh(prop)
    return prop


@router.delete("/properties/{property_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_property(
    property_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_landlord_or_caretaker),
) -> None:
    _ensure_landlord_or_admin(current_user)
    prop = await _get_accessible_property(db, property_id, current_user)
    await db.delete(prop)


# ---------------------------------------------------------------------------
# Units (Mieteinheiten)
# ---------------------------------------------------------------------------


@router.get("/properties/{property_id}/units", response_model=list[UnitRead])
async def list_units(
    property_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_landlord_or_caretaker),
) -> list[Unit]:
    await _get_accessible_property(db, property_id, current_user)
    result = await db.execute(select(Unit).where(Unit.property_id == property_id).order_by(Unit.name))
    return list(result.scalars().all())


@router.post("/properties/{property_id}/units", response_model=UnitRead, status_code=status.HTTP_201_CREATED)
async def create_unit(
    property_id: str,
    payload: UnitCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_landlord_or_caretaker),
) -> Unit:
    _ensure_landlord_or_admin(current_user)
    await _get_accessible_property(db, property_id, current_user)
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
    current_user: User = Depends(require_landlord_or_caretaker),
) -> Unit:
    _ensure_landlord_or_admin(current_user)
    unit = await _get_accessible_unit(db, unit_id, property_id, current_user)
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
    current_user: User = Depends(require_landlord_or_caretaker),
) -> None:
    _ensure_landlord_or_admin(current_user)
    unit = await _get_accessible_unit(db, unit_id, property_id, current_user)
    await db.delete(unit)


# ---------------------------------------------------------------------------
# Meters (Zähler)
# ---------------------------------------------------------------------------


@router.post("/units/{unit_id}/meters", response_model=MeterRead, status_code=status.HTTP_201_CREATED)
async def create_meter(
    unit_id: str,
    payload: MeterCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_landlord_or_caretaker),
) -> Meter:
    await _assert_unit_access(db, unit_id, current_user)
    meter = Meter(**payload.model_dump(), unit_id=unit_id)
    db.add(meter)
    await db.flush()
    await db.refresh(meter)
    return meter


@router.get("/units/{unit_id}/meters", response_model=list[MeterRead])
async def list_meters(
    unit_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_landlord_or_caretaker),
) -> list[Meter]:
    await _assert_unit_access(db, unit_id, current_user)
    result = await db.execute(select(Meter).where(Meter.unit_id == unit_id))
    return list(result.scalars().all())


@router.post("/meters/{meter_id}/readings", response_model=MeterReadingRead, status_code=status.HTTP_201_CREATED)
async def add_reading(
    meter_id: str,
    payload: MeterReadingCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_landlord_or_caretaker),
) -> MeterReading:
    await _assert_meter_access(db, meter_id, current_user)
    reading = MeterReading(**payload.model_dump(), meter_id=meter_id, uploaded_by_id=current_user.id)
    db.add(reading)
    await db.flush()
    await db.refresh(reading)
    return reading


@router.get("/meters/{meter_id}/readings", response_model=list[MeterReadingRead])
async def list_readings(
    meter_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_landlord_or_caretaker),
) -> list[MeterReading]:
    await _assert_meter_access(db, meter_id, current_user)
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
    current_user: User = Depends(require_landlord_or_caretaker),
) -> list[Contract]:
    result = await db.execute(_contract_visibility_stmt(current_user))
    return list(result.scalars().all())


@router.post("/contracts", response_model=ContractRead, status_code=status.HTTP_201_CREATED)
async def create_contract(
    payload: ContractCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_landlord_or_caretaker),
) -> Contract:
    await _assert_unit_access(db, payload.unit_id, current_user)
    # Verify tenant exists
    tenant_result = await db.execute(select(User).where(User.id == payload.tenant_id, User.role == UserRole.TENANT))
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
    current_user: User = Depends(require_landlord_or_caretaker),
) -> Contract:
    contract = await _get_accessible_contract(db, contract_id, current_user)
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
    current_user: User = Depends(require_landlord_or_caretaker),
) -> Contract:
    contract = await _get_accessible_contract(db, contract_id, current_user)
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
    current_user: User = Depends(require_landlord_or_caretaker),
) -> list[UtilityBill]:
    result = await db.execute(_bill_visibility_stmt(current_user))
    return list(result.scalars().all())


@router.patch("/utility-bills/{bill_id}/status", response_model=UtilityBillRead)
async def update_bill_status(
    bill_id: str,
    payload: UtilityBillStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_landlord_or_caretaker),
) -> UtilityBill:
    bill = await _get_accessible_bill(db, bill_id, current_user)
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
    current_user: User = Depends(require_landlord_or_caretaker),
) -> list[User]:
    """Return all tenants that have/had a contract in any of this landlord's units."""
    result = await db.execute(
        select(User)
        .join(Contract, Contract.tenant_id == User.id)
        .join(Unit, Contract.unit_id == Unit.id)
        .join(Property, Unit.property_id == Property.id)
        .where(_property_access_condition(current_user))
        .distinct()
    )
    return list(result.scalars().all())


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _ensure_landlord_or_admin(current_user: User) -> None:
    if current_user.role not in (UserRole.LANDLORD, UserRole.ADMIN):
        raise HTTPException(status_code=403, detail="Only landlord/admin can modify building structure")


def _property_access_condition(current_user: User):
    if current_user.role == UserRole.ADMIN:
        return True
    if current_user.role == UserRole.LANDLORD:
        return Property.landlord_id == current_user.id

    building_ids = select(CaretakerBuildingAssignment.building_id).where(
        CaretakerBuildingAssignment.caretaker_id == current_user.id
    )
    apartment_building_ids = (
        select(Unit.property_id)
        .join(CaretakerApartmentAssignment, CaretakerApartmentAssignment.apartment_id == Unit.id)
        .where(CaretakerApartmentAssignment.caretaker_id == current_user.id)
    )
    return or_(Property.id.in_(building_ids), Property.id.in_(apartment_building_ids))


def _property_visibility_stmt(current_user: User):
    return select(Property).where(_property_access_condition(current_user)).order_by(Property.name)


async def _get_accessible_property(db: AsyncSession, property_id: str, current_user: User) -> Property:
    result = await db.execute(
        select(Property).where(Property.id == property_id, _property_access_condition(current_user))
    )
    prop = result.scalar_one_or_none()
    if not prop:
        raise HTTPException(status_code=404, detail="Building not found or access denied")
    return prop


async def _get_accessible_unit(db: AsyncSession, unit_id: str, property_id: str, current_user: User) -> Unit:
    result = await db.execute(
        select(Unit)
        .join(Property, Unit.property_id == Property.id)
        .where(Unit.id == unit_id, Unit.property_id == property_id, _property_access_condition(current_user))
    )
    unit = result.scalar_one_or_none()
    if not unit:
        raise HTTPException(status_code=404, detail="Apartment not found or access denied")
    return unit


async def _assert_unit_access(db: AsyncSession, unit_id: str, current_user: User) -> Unit:
    result = await db.execute(
        select(Unit)
        .join(Property, Unit.property_id == Property.id)
        .where(Unit.id == unit_id, _property_access_condition(current_user))
    )
    unit = result.scalar_one_or_none()
    if not unit:
        raise HTTPException(status_code=404, detail="Apartment not found or access denied")
    return unit


async def _assert_meter_access(db: AsyncSession, meter_id: str, current_user: User) -> Meter:
    result = await db.execute(
        select(Meter)
        .join(Unit, Meter.unit_id == Unit.id)
        .join(Property, Unit.property_id == Property.id)
        .where(Meter.id == meter_id, _property_access_condition(current_user))
    )
    meter = result.scalar_one_or_none()
    if not meter:
        raise HTTPException(status_code=404, detail="Meter not found or access denied")
    return meter


def _contract_visibility_stmt(current_user: User):
    return (
        select(Contract)
        .join(Unit, Contract.unit_id == Unit.id)
        .join(Property, Unit.property_id == Property.id)
        .where(_property_access_condition(current_user))
    )


async def _get_accessible_contract(db: AsyncSession, contract_id: str, current_user: User) -> Contract:
    result = await db.execute(_contract_visibility_stmt(current_user).where(Contract.id == contract_id))
    contract = result.scalar_one_or_none()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found or access denied")
    return contract


def _bill_visibility_stmt(current_user: User):
    return (
        select(UtilityBill)
        .options(selectinload(UtilityBill.line_items))
        .join(Contract, UtilityBill.contract_id == Contract.id)
        .join(Unit, Contract.unit_id == Unit.id)
        .join(Property, Unit.property_id == Property.id)
        .where(_property_access_condition(current_user))
    )


async def _get_accessible_bill(db: AsyncSession, bill_id: str, current_user: User) -> UtilityBill:
    result = await db.execute(_bill_visibility_stmt(current_user).where(UtilityBill.id == bill_id))
    bill = result.scalar_one_or_none()
    if not bill:
        raise HTTPException(status_code=404, detail="Utility bill not found or access denied")
    return bill


async def _assert_caretaker_exists(db: AsyncSession, caretaker_id: str) -> User:
    caretaker = await db.scalar(
        select(User).where(User.id == caretaker_id, User.role == UserRole.CARETAKER, User.is_active == True)  # noqa: E712
    )
    if caretaker is None:
        raise HTTPException(status_code=404, detail="Caretaker not found")
    return caretaker


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
