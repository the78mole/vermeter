from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.models import (
    ContractStatus,
    HeatingType,
    MeterType,
    UserRole,
    UtilityBillStatus,
)


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------


class OrmModel(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


# ---------------------------------------------------------------------------
# User  (read-only – management happens in Keycloak)
# ---------------------------------------------------------------------------


class UserRead(OrmModel):
    id: str
    email: str
    full_name: str
    role: UserRole
    admin_role: AdminRole | None = None
    is_active: bool
    created_at: datetime


# ---------------------------------------------------------------------------
# Admin-User management
# ---------------------------------------------------------------------------


class AdminUserCreate(BaseModel):
    email: str
    full_name: str
    admin_role: AdminRole


class AdminUserUpdate(BaseModel):
    full_name: str | None = None
    admin_role: AdminRole | None = None
    is_active: bool | None = None


class AdminUserProvisionResponse(UserRead):
    keycloak_created: bool = False
    temp_password: str | None = None


class LandlordCreate(BaseModel):
    email: str
    full_name: str


class LandlordUpdate(BaseModel):
    full_name: str | None = None
    is_active: bool | None = None


class LandlordProvisionResponse(UserRead):
    """Response payload for POST /admin/landlords.

    Extends :class:`UserRead` with the one-time temporary password that was
    set in Keycloak.  The password is only returned once and never stored.
    """

    keycloak_created: bool = False
    temp_password: str | None = None


# ---------------------------------------------------------------------------
# LandlordProfile
# ---------------------------------------------------------------------------


class LandlordProfileRead(OrmModel):
    id: str
    user_id: str
    phone: str | None = None
    website: str | None = None
    company_name: str | None = None
    address_street: str | None = None
    address_city: str | None = None
    address_zip: str | None = None
    address_country: str | None = None
    tax_id: str | None = None
    vat_id: str | None = None
    iban: str | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime


class LandlordProfileUpsert(BaseModel):
    """Used for both create and update (PUT semantics – missing fields stay None)."""

    phone: str | None = None
    website: str | None = None
    company_name: str | None = None
    address_street: str | None = None
    address_city: str | None = None
    address_zip: str | None = None
    address_country: str | None = None
    tax_id: str | None = None
    vat_id: str | None = None
    iban: str | None = None
    notes: str | None = None


class LandlordWithProfile(UserRead):
    """UserRead + optional LandlordProfile – used in admin landlord list/detail."""

    # The ORM relationship is named 'landlord_profile'; alias it to 'profile' for the API.
    profile: LandlordProfileRead | None = Field(None, validation_alias="landlord_profile")


# ---------------------------------------------------------------------------
# Tag
# ---------------------------------------------------------------------------


class TagRead(OrmModel):
    id: int
    name: str


# ---------------------------------------------------------------------------
# LandlordDocument
# ---------------------------------------------------------------------------


class LandlordDocumentRead(OrmModel):
    id: str
    landlord_id: str
    filename: str
    content_type: str
    size_bytes: int
    description: str | None = None
    tags: list[TagRead] = []
    uploaded_at: datetime


class LandlordDocumentUpdate(BaseModel):
    tags: list[str] = []
    description: str | None = None


# ---------------------------------------------------------------------------
# Property
# ---------------------------------------------------------------------------


class PropertyCreate(BaseModel):
    name: str
    address_street: str
    address_city: str
    address_zip: str
    address_country: str = "Germany"


class PropertyUpdate(BaseModel):
    name: str | None = None
    address_street: str | None = None
    address_city: str | None = None
    address_zip: str | None = None
    address_country: str | None = None


class PropertyRead(OrmModel):
    id: str
    landlord_id: str
    name: str
    address_street: str
    address_city: str
    address_zip: str
    address_country: str
    created_at: datetime


# ---------------------------------------------------------------------------
# Unit (Mieteinheit)
# ---------------------------------------------------------------------------


class UnitCreate(BaseModel):
    name: str
    floor: int | None = None
    square_meters: Decimal
    rooms: Decimal | None = None
    heating_type: HeatingType = HeatingType.GAS


class UnitUpdate(BaseModel):
    name: str | None = None
    floor: int | None = None
    square_meters: Decimal | None = None
    rooms: Decimal | None = None
    heating_type: HeatingType | None = None
    is_occupied: bool | None = None


class UnitRead(OrmModel):
    id: str
    property_id: str
    name: str
    floor: int | None
    square_meters: Decimal
    rooms: Decimal | None
    heating_type: HeatingType
    is_occupied: bool
    created_at: datetime


# ---------------------------------------------------------------------------
# Meter (Zähler)
# ---------------------------------------------------------------------------


class MeterCreate(BaseModel):
    meter_type: MeterType
    serial_number: str | None = None
    description: str | None = None
    is_virtual: bool = False


class MeterRead(OrmModel):
    id: str
    unit_id: str
    meter_type: MeterType
    serial_number: str | None
    description: str | None
    is_virtual: bool


# ---------------------------------------------------------------------------
# MeterReading (Zählerstand)
# ---------------------------------------------------------------------------


class MeterReadingCreate(BaseModel):
    reading_date: date
    value: Decimal
    unit_of_measure: str = "kWh"
    image_url: str | None = None
    notes: str | None = None


class MeterReadingRead(OrmModel):
    id: str
    meter_id: str
    uploaded_by_id: str | None
    reading_date: date
    value: Decimal
    unit_of_measure: str
    image_url: str | None
    notes: str | None
    is_interpolated: bool
    created_at: datetime


class InterpolatedReadingRead(OrmModel):
    id: str
    meter_id: str
    period_start: date
    period_end: date
    value_start: Decimal
    value_end: Decimal
    consumption: Decimal
    created_at: datetime


# ---------------------------------------------------------------------------
# Contract (Mietvertrag)
# ---------------------------------------------------------------------------


class ContractCreate(BaseModel):
    unit_id: str
    tenant_id: str
    start_date: date
    end_date: date | None = None
    monthly_rent: Decimal
    deposit: Decimal | None = None
    advance_payment_utilities: Decimal = Decimal("0")
    notes: str | None = None


class ContractUpdate(BaseModel):
    end_date: date | None = None
    monthly_rent: Decimal | None = None
    deposit: Decimal | None = None
    advance_payment_utilities: Decimal | None = None
    notes: str | None = None


class ContractStatusUpdate(BaseModel):
    status: ContractStatus


class ContractRead(OrmModel):
    id: str
    unit_id: str
    tenant_id: str
    status: ContractStatus
    start_date: date
    end_date: date | None
    monthly_rent: Decimal
    deposit: Decimal | None
    advance_payment_utilities: Decimal
    signed_at: datetime | None
    terminated_at: datetime | None
    notes: str | None
    created_at: datetime


# ---------------------------------------------------------------------------
# UtilityBill (Nebenkostenabrechnung)
# ---------------------------------------------------------------------------


class BillLineItemRead(OrmModel):
    id: str
    description: str
    cost_type: str
    total_amount: Decimal
    unit_share: Decimal
    distribution_key: str | None
    notes: str | None


class UtilityBillRead(OrmModel):
    id: str
    contract_id: str
    status: UtilityBillStatus
    billing_period_start: date
    billing_period_end: date
    total_cost: Decimal
    heating_cost: Decimal
    water_cost: Decimal
    electricity_cost: Decimal
    operating_cost: Decimal
    advance_payments_total: Decimal
    balance: Decimal
    pdf_url: str | None
    sent_at: datetime | None
    paid_at: datetime | None
    disputed_at: datetime | None
    created_at: datetime
    line_items: list[BillLineItemRead] = []


class UtilityBillStatusUpdate(BaseModel):
    status: UtilityBillStatus


# ---------------------------------------------------------------------------
# Graph Engine (Node-Based Billing)
# ---------------------------------------------------------------------------


class NodePort(BaseModel):
    name: str
    value: float | None = None


class SourceNodeData(BaseModel):
    meter_id: str
    period_start: date
    period_end: date


class MathNodeData(BaseModel):
    formula: str = "inputA + inputB"
    factor: float = 1.0


class SplitterNodeData(BaseModel):
    ratio: float = Field(0.3, ge=0.0, le=1.0)  # fraction going to output_a


class SinkNodeData(BaseModel):
    contract_id: str
    cost_type: str
    description: str


class GraphNode(BaseModel):
    id: str
    type: str  # source | math | splitter | sink
    data: dict[str, Any]
    inputs: list[str] = []  # node IDs that feed into this node


class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    source_handle: str | None = None
    target_handle: str | None = None


class BillingGraph(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    preview_mode: bool = False
    sample_data: dict[str, float] | None = None


class GraphCalculationResult(BaseModel):
    node_results: dict[str, Any]
    calculation_trace: dict[str, Any]
    errors: list[str] = []
