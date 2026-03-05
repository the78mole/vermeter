"""BillingEngine – calculates Nebenkostenabrechnung (utility bills).

Distribution keys:
  - AREA: Grundkosten split proportional to unit.square_meters / total_area
  - CONSUMPTION: Verbrauchskosten split proportional to consumed units

HeizkostenV guidance:
  - Heating base cost (Grundkosten):  30–50% distributed by area
  - Heating consumption cost:         50–70% distributed by consumption
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import (
    BillLineItem,
    Contract,
    ContractStatus,
    Meter,
    MeterReading,
    Property,
    Unit,
    UtilityBill,
    UtilityBillStatus,
)

logger = logging.getLogger(__name__)


@dataclass
class CostInput:
    """A single cost position to be distributed among units."""

    description: str
    cost_type: str  # e.g. HEATING_BASE, HEATING_CONSUMPTION, WATER, ELECTRICITY, OPERATING
    total_amount: Decimal
    distribution_key: str  # AREA | CONSUMPTION
    meter_type: str | None = None  # only needed for CONSUMPTION distribution


@dataclass
class BillingContext:
    """All data required to calculate a single unit's share of costs."""

    unit: Unit
    unit_area: Decimal
    total_area: Decimal  # sum of all active units' areas in the property
    unit_consumption: dict[str, Decimal] = field(default_factory=dict)  # meter_type -> consumed units
    total_consumption: dict[str, Decimal] = field(default_factory=dict)


class BillingEngine:
    """Calculate the Nebenkostenabrechnung for a given contract and billing period."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def calculate(
        self,
        contract_id: str,
        billing_period_start: date,
        billing_period_end: date,
        cost_inputs: list[CostInput],
        base_ratio: Decimal = Decimal("0.30"),  # 30% Grundkosten by area
    ) -> UtilityBill:
        """
        Main entry point.  Creates (or updates) the UtilityBill for the given contract.
        """
        contract = await self._get_contract(contract_id)
        unit = await self._get_unit(contract.unit_id)
        property_ = await self._get_property(unit.property_id)

        total_area, active_units = await self._get_active_area_and_units(property_.id)
        consumptions = await self._get_consumptions(unit.id, billing_period_start, billing_period_end)
        total_consumptions = await self._get_total_consumptions(property_.id, billing_period_start, billing_period_end)

        ctx = BillingContext(
            unit=unit,
            unit_area=Decimal(str(unit.square_meters)),
            total_area=total_area,
            unit_consumption=consumptions,
            total_consumption=total_consumptions,
        )

        bill = UtilityBill(
            contract_id=contract_id,
            status=UtilityBillStatus.REVIEW_REQUIRED,
            billing_period_start=billing_period_start,
            billing_period_end=billing_period_end,
        )
        self.db.add(bill)
        await self.db.flush()  # get bill.id

        total = Decimal("0")
        heating_cost = Decimal("0")
        water_cost = Decimal("0")
        electricity_cost = Decimal("0")
        operating_cost = Decimal("0")

        for cost_input in cost_inputs:
            unit_share = self._calculate_share(cost_input, ctx)

            item = BillLineItem(
                bill_id=bill.id,
                description=cost_input.description,
                cost_type=cost_input.cost_type,
                total_amount=cost_input.total_amount,
                unit_share=unit_share,
                distribution_key=cost_input.distribution_key,
            )
            self.db.add(item)
            total += unit_share

            cost_type_lower = cost_input.cost_type.upper()
            if "HEAT" in cost_type_lower:
                heating_cost += unit_share
            elif "WATER" in cost_type_lower:
                water_cost += unit_share
            elif "ELECTRICITY" in cost_type_lower:
                electricity_cost += unit_share
            else:
                operating_cost += unit_share

        advance = Decimal(str(contract.advance_payment_utilities)) * self._months_in_period(
            billing_period_start, billing_period_end
        )

        bill.total_cost = total
        bill.heating_cost = heating_cost
        bill.water_cost = water_cost
        bill.electricity_cost = electricity_cost
        bill.operating_cost = operating_cost
        bill.advance_payments_total = advance
        bill.balance = total - advance

        await self.db.flush()
        return bill

    # ------------------------------------------------------------------
    # Distribution calculation
    # ------------------------------------------------------------------

    def _calculate_share(self, cost_input: CostInput, ctx: BillingContext) -> Decimal:
        if cost_input.distribution_key == "AREA":
            return self._area_share(cost_input.total_amount, ctx.unit_area, ctx.total_area)
        if cost_input.distribution_key == "CONSUMPTION" and cost_input.meter_type:
            unit_cons = ctx.unit_consumption.get(cost_input.meter_type, Decimal("0"))
            total_cons = ctx.total_consumption.get(cost_input.meter_type, Decimal("0"))
            return self._consumption_share(cost_input.total_amount, unit_cons, total_cons)
        # Fallback to area
        return self._area_share(cost_input.total_amount, ctx.unit_area, ctx.total_area)

    @staticmethod
    def _area_share(total: Decimal, unit_area: Decimal, total_area: Decimal) -> Decimal:
        """UnitCost = TotalCost × (UnitArea / TotalArea)"""
        if total_area == 0:
            return Decimal("0")
        share = total * (unit_area / total_area)
        return share.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @staticmethod
    def _consumption_share(total: Decimal, unit_consumption: Decimal, total_consumption: Decimal) -> Decimal:
        if total_consumption == 0:
            return Decimal("0")
        share = total * (unit_consumption / total_consumption)
        return share.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @staticmethod
    def _months_in_period(start: date, end: date) -> Decimal:
        months = (end.year - start.year) * 12 + (end.month - start.month) + 1
        return Decimal(str(max(months, 1)))

    # ------------------------------------------------------------------
    # DB helpers
    # ------------------------------------------------------------------

    async def _get_contract(self, contract_id: str) -> Contract:
        result = await self.db.execute(select(Contract).where(Contract.id == contract_id))
        contract = result.scalar_one_or_none()
        if not contract:
            raise ValueError(f"Contract {contract_id} not found")
        return contract

    async def _get_unit(self, unit_id: str) -> Unit:
        result = await self.db.execute(select(Unit).where(Unit.id == unit_id))
        return result.scalar_one()

    async def _get_property(self, property_id: str) -> Property:
        result = await self.db.execute(select(Property).where(Property.id == property_id))
        return result.scalar_one()

    async def _get_active_area_and_units(self, property_id: str) -> tuple[Decimal, list[Unit]]:
        result = await self.db.execute(
            select(Unit)
            .join(Property, Unit.property_id == Property.id)
            .where(Property.id == property_id, Unit.is_occupied == True)  # noqa: E712
        )
        units = list(result.scalars().all())
        total_area = sum((Decimal(str(u.square_meters)) for u in units), Decimal("0"))
        return total_area, units

    async def _get_consumptions(
        self, unit_id: str, period_start: date, period_end: date
    ) -> dict[str, Decimal]:
        """Return consumption per meter_type for a specific unit in the billing period."""
        result = await self.db.execute(
            select(Meter).where(Meter.unit_id == unit_id)
        )
        meters = list(result.scalars().all())
        consumptions: dict[str, Decimal] = {}
        for meter in meters:
            consumption = await self._meter_consumption(meter.id, period_start, period_end)
            key = meter.meter_type.value
            consumptions[key] = consumptions.get(key, Decimal("0")) + consumption
        return consumptions

    async def _get_total_consumptions(
        self, property_id: str, period_start: date, period_end: date
    ) -> dict[str, Decimal]:
        result = await self.db.execute(
            select(Meter)
            .join(Unit, Meter.unit_id == Unit.id)
            .where(Unit.property_id == property_id)
        )
        meters = list(result.scalars().all())
        totals: dict[str, Decimal] = {}
        for meter in meters:
            consumption = await self._meter_consumption(meter.id, period_start, period_end)
            key = meter.meter_type.value
            totals[key] = totals.get(key, Decimal("0")) + consumption
        return totals

    async def _meter_consumption(self, meter_id: str, period_start: date, period_end: date) -> Decimal:
        """Difference between the last reading before/on period_end and the first reading on/after period_start."""
        result_start = await self.db.execute(
            select(MeterReading)
            .where(MeterReading.meter_id == meter_id, MeterReading.reading_date <= period_start)
            .order_by(MeterReading.reading_date.desc())
            .limit(1)
        )
        reading_start = result_start.scalar_one_or_none()

        result_end = await self.db.execute(
            select(MeterReading)
            .where(MeterReading.meter_id == meter_id, MeterReading.reading_date <= period_end)
            .order_by(MeterReading.reading_date.desc())
            .limit(1)
        )
        reading_end = result_end.scalar_one_or_none()

        if not reading_start or not reading_end:
            return Decimal("0")
        consumption = Decimal(str(reading_end.value)) - Decimal(str(reading_start.value))
        return max(consumption, Decimal("0"))
