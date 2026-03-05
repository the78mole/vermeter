import enum
import uuid
from datetime import date, datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class UserRole(str, enum.Enum):
    LANDLORD = "LANDLORD"
    TENANT = "TENANT"
    ADMIN = "ADMIN"


class HeatingType(str, enum.Enum):
    GAS = "GAS"
    OIL = "OIL"
    HEAT_PUMP = "HEAT_PUMP"
    DISTRICT_HEATING = "DISTRICT_HEATING"
    PELLET = "PELLET"
    ELECTRICITY = "ELECTRICITY"
    SOLAR = "SOLAR"


class ContractStatus(str, enum.Enum):
    """State machine: DRAFT -> PENDING_SIGNATURE -> ACTIVE -> TERMINATED -> ARCHIVED"""

    DRAFT = "DRAFT"
    PENDING_SIGNATURE = "PENDING_SIGNATURE"
    ACTIVE = "ACTIVE"
    TERMINATED = "TERMINATED"
    ARCHIVED = "ARCHIVED"


class UtilityBillStatus(str, enum.Enum):
    """State machine: CALCULATING -> REVIEW_REQUIRED -> SENT_TO_TENANT -> PAID -> DISPUTED"""

    CALCULATING = "CALCULATING"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    SENT_TO_TENANT = "SENT_TO_TENANT"
    PAID = "PAID"
    DISPUTED = "DISPUTED"


class MeterType(str, enum.Enum):
    WATER_COLD = "WATER_COLD"
    WATER_HOT = "WATER_HOT"
    HEAT = "HEAT"
    ELECTRICITY = "ELECTRICITY"
    GAS = "GAS"
    OIL = "OIL"


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _uuid() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# User (Landlord / Tenant)
# ---------------------------------------------------------------------------


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.TENANT)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_now, onupdate=_now, nullable=False)

    # Relationships
    owned_properties = relationship("Property", back_populates="landlord", cascade="all, delete-orphan")
    contracts = relationship("Contract", back_populates="tenant", foreign_keys="Contract.tenant_id")
    meter_readings = relationship("MeterReading", back_populates="uploaded_by")


# ---------------------------------------------------------------------------
# Property (Immobilie)
# ---------------------------------------------------------------------------


class Property(Base):
    __tablename__ = "properties"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    landlord_id = Column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    address_street = Column(String(255), nullable=False)
    address_city = Column(String(255), nullable=False)
    address_zip = Column(String(20), nullable=False)
    address_country = Column(String(100), default="Germany")
    created_at = Column(DateTime(timezone=True), default=_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_now, onupdate=_now, nullable=False)

    landlord = relationship("User", back_populates="owned_properties")
    units = relationship("Unit", back_populates="property", cascade="all, delete-orphan")


# ---------------------------------------------------------------------------
# Unit (Mieteinheit)
# ---------------------------------------------------------------------------


class Unit(Base):
    __tablename__ = "units"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    property_id = Column(UUID(as_uuid=False), ForeignKey("properties.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    floor = Column(Integer, nullable=True)
    square_meters = Column(Numeric(10, 2), nullable=False)
    rooms = Column(Numeric(5, 1), nullable=True)
    heating_type = Column(Enum(HeatingType), nullable=False, default=HeatingType.GAS)
    is_occupied = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_now, onupdate=_now, nullable=False)

    property = relationship("Property", back_populates="units")
    contracts = relationship("Contract", back_populates="unit")
    meters = relationship("Meter", back_populates="unit", cascade="all, delete-orphan")


# ---------------------------------------------------------------------------
# Meter (Zähler)
# ---------------------------------------------------------------------------


class Meter(Base):
    __tablename__ = "meters"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    unit_id = Column(UUID(as_uuid=False), ForeignKey("units.id", ondelete="CASCADE"), nullable=False)
    meter_type = Column(Enum(MeterType), nullable=False)
    serial_number = Column(String(100), nullable=True)
    description = Column(String(255), nullable=True)
    # Virtual meter: sums up multiple physical meters
    is_virtual = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_now, nullable=False)

    unit = relationship("Unit", back_populates="meters")
    readings = relationship("MeterReading", back_populates="meter", cascade="all, delete-orphan")
    # Source meters for virtual meters
    source_meters = relationship(
        "VirtualMeterSource",
        foreign_keys="VirtualMeterSource.virtual_meter_id",
        back_populates="virtual_meter",
        cascade="all, delete-orphan",
    )


class VirtualMeterSource(Base):
    """Links a virtual meter to its physical source meters."""

    __tablename__ = "virtual_meter_sources"
    __table_args__ = (UniqueConstraint("virtual_meter_id", "source_meter_id"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    virtual_meter_id = Column(UUID(as_uuid=False), ForeignKey("meters.id", ondelete="CASCADE"), nullable=False)
    source_meter_id = Column(UUID(as_uuid=False), ForeignKey("meters.id", ondelete="CASCADE"), nullable=False)
    factor = Column(Float, default=1.0)

    virtual_meter = relationship("Meter", foreign_keys=[virtual_meter_id], back_populates="source_meters")
    source_meter = relationship("Meter", foreign_keys=[source_meter_id])


# ---------------------------------------------------------------------------
# MeterReading (Zählerstand)
# ---------------------------------------------------------------------------


class MeterReading(Base):
    __tablename__ = "meter_readings"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    meter_id = Column(UUID(as_uuid=False), ForeignKey("meters.id", ondelete="CASCADE"), nullable=False)
    uploaded_by_id = Column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reading_date = Column(Date, nullable=False)
    value = Column(Numeric(15, 3), nullable=False)
    unit_of_measure = Column(String(20), default="kWh")
    image_url = Column(String(500), nullable=True)
    notes = Column(Text, nullable=True)
    is_interpolated = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_now, nullable=False)

    meter = relationship("Meter", back_populates="readings")
    uploaded_by = relationship("User", back_populates="meter_readings")


# ---------------------------------------------------------------------------
# InterpolatedReading (for tenant dashboard)
# ---------------------------------------------------------------------------


class InterpolatedReading(Base):
    __tablename__ = "interpolated_readings"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    meter_id = Column(UUID(as_uuid=False), ForeignKey("meters.id", ondelete="CASCADE"), nullable=False)
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)
    value_start = Column(Numeric(15, 3), nullable=False)
    value_end = Column(Numeric(15, 3), nullable=False)
    consumption = Column(Numeric(15, 3), nullable=False)
    created_at = Column(DateTime(timezone=True), default=_now, nullable=False)

    meter = relationship("Meter")


# ---------------------------------------------------------------------------
# Contract (Mietvertrag)
# ---------------------------------------------------------------------------


class Contract(Base):
    __tablename__ = "contracts"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    unit_id = Column(UUID(as_uuid=False), ForeignKey("units.id", ondelete="RESTRICT"), nullable=False)
    tenant_id = Column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    status = Column(Enum(ContractStatus), nullable=False, default=ContractStatus.DRAFT)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)
    monthly_rent = Column(Numeric(10, 2), nullable=False)
    deposit = Column(Numeric(10, 2), nullable=True)
    advance_payment_utilities = Column(Numeric(10, 2), default=0)
    signed_at = Column(DateTime(timezone=True), nullable=True)
    terminated_at = Column(DateTime(timezone=True), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_now, onupdate=_now, nullable=False)

    unit = relationship("Unit", back_populates="contracts")
    tenant = relationship("User", back_populates="contracts", foreign_keys=[tenant_id])
    utility_bills = relationship("UtilityBill", back_populates="contract", cascade="all, delete-orphan")


# ---------------------------------------------------------------------------
# UtilityBill (Nebenkostenabrechnung)
# ---------------------------------------------------------------------------


class UtilityBill(Base):
    __tablename__ = "utility_bills"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    contract_id = Column(UUID(as_uuid=False), ForeignKey("contracts.id", ondelete="CASCADE"), nullable=False)
    status = Column(Enum(UtilityBillStatus), nullable=False, default=UtilityBillStatus.CALCULATING)
    billing_period_start = Column(Date, nullable=False)
    billing_period_end = Column(Date, nullable=False)
    # Costs breakdown
    total_cost = Column(Numeric(12, 2), default=0)
    heating_cost = Column(Numeric(12, 2), default=0)
    water_cost = Column(Numeric(12, 2), default=0)
    electricity_cost = Column(Numeric(12, 2), default=0)
    operating_cost = Column(Numeric(12, 2), default=0)
    advance_payments_total = Column(Numeric(12, 2), default=0)
    balance = Column(Numeric(12, 2), default=0)  # positive = tenant owes, negative = landlord refunds
    # Graph-based calculation trace (JSONB)
    calculation_trace = Column(JSON, nullable=True)
    pdf_url = Column(String(500), nullable=True)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    paid_at = Column(DateTime(timezone=True), nullable=True)
    disputed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_now, onupdate=_now, nullable=False)

    contract = relationship("Contract", back_populates="utility_bills")
    line_items = relationship("BillLineItem", back_populates="bill", cascade="all, delete-orphan")


class BillLineItem(Base):
    __tablename__ = "bill_line_items"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    bill_id = Column(UUID(as_uuid=False), ForeignKey("utility_bills.id", ondelete="CASCADE"), nullable=False)
    description = Column(String(500), nullable=False)
    cost_type = Column(String(100), nullable=False)  # e.g. HEATING_BASE, HEATING_CONSUMPTION, WATER, ...
    total_amount = Column(Numeric(12, 2), nullable=False)
    unit_share = Column(Numeric(12, 2), nullable=False)
    distribution_key = Column(String(100), nullable=True)  # AREA | CONSUMPTION | PERSON
    notes = Column(Text, nullable=True)

    bill = relationship("UtilityBill", back_populates="line_items")
