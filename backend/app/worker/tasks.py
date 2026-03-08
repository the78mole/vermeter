"""Celery tasks for the Rental Manager.

- generate_bill_pdf: Generate a PDF for a UtilityBill and store the URL.
- daily_aggregator:  Fetch raw meter readings, pro-rata interpolate them to
                     monthly periods, and store InterpolatedReadings for the
                     tenant dashboard.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import date, timedelta
from decimal import Decimal

from celery import shared_task

from app.worker.celery_app import celery_app

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# PDF Generation
# ---------------------------------------------------------------------------


@celery_app.task(name="app.worker.tasks.generate_bill_pdf", bind=True, max_retries=3)
def generate_bill_pdf(self, bill_id: str) -> dict:
    """Generate a PDF for a UtilityBill and update the pdf_url field."""
    try:
        result = asyncio.run(_generate_pdf_async(bill_id))
        return result
    except Exception as exc:
        logger.exception("PDF generation failed for bill %s", bill_id)
        raise self.retry(exc=exc, countdown=60) from exc


async def _generate_pdf_async(bill_id: str) -> dict:
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    from app.core.database import AsyncSessionLocal
    from app.models.models import Contract, Unit, User, UtilityBill

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(UtilityBill)
            .options(selectinload(UtilityBill.line_items))
            .where(UtilityBill.id == bill_id)
        )
        bill = result.scalar_one_or_none()
        if not bill:
            return {"error": f"Bill {bill_id} not found"}

        # Load contract + tenant info
        contract_result = await db.execute(
            select(Contract)
            .options(selectinload(Contract.unit))
            .where(Contract.id == bill.contract_id)
        )
        contract = contract_result.scalar_one()

        tenant_result = await db.execute(select(User).where(User.id == contract.tenant_id))
        tenant = tenant_result.scalar_one()

        pdf_path = await _build_pdf(bill, contract, tenant)

        bill.pdf_url = pdf_path
        await db.commit()

    return {"bill_id": bill_id, "pdf_url": pdf_path}


async def _build_pdf(bill: object, contract: object, tenant: object) -> str:
    """Build a simple PDF using ReportLab and return the file path."""
    import os

    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib import colors

    from app.core.config import settings

    upload_dir = settings.UPLOAD_DIR
    os.makedirs(upload_dir, exist_ok=True)
    filename = f"bill_{bill.id}.pdf"  # type: ignore[attr-defined]
    filepath = os.path.join(upload_dir, filename)

    doc = SimpleDocTemplate(filepath, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph("Nebenkostenabrechnung", styles["Title"]))
    elements.append(Spacer(1, 0.5 * cm))
    elements.append(Paragraph(f"Mieter: {tenant.full_name}", styles["Normal"]))  # type: ignore[attr-defined]
    elements.append(
        Paragraph(
            f"Abrechnungszeitraum: {bill.billing_period_start} – {bill.billing_period_end}",  # type: ignore[attr-defined]
            styles["Normal"],
        )
    )
    elements.append(Spacer(1, 0.5 * cm))

    data = [["Kostenposition", "Gesamt (€)", "Ihr Anteil (€)", "Schlüssel"]]
    for item in bill.line_items:  # type: ignore[attr-defined]
        data.append([
            item.description,
            str(item.total_amount),
            str(item.unit_share),
            item.distribution_key or "",
        ])
    data.append(["Summe", "", str(bill.total_cost), ""])
    data.append(["Vorauszahlungen", "", str(bill.advance_payments_total), ""])
    balance_label = "Nachzahlung" if bill.balance >= 0 else "Guthaben"
    data.append([balance_label, "", str(abs(bill.balance)), ""])

    table = Table(data, colWidths=[9 * cm, 3 * cm, 3 * cm, 3 * cm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
    ]))
    elements.append(table)
    doc.build(elements)

    return f"/uploads/{filename}"


# ---------------------------------------------------------------------------
# Daily Meter Aggregator (Celery Beat task)
# ---------------------------------------------------------------------------


@celery_app.task(name="app.worker.tasks.daily_aggregator")
def daily_aggregator() -> dict:
    """
    Daily task that:
    1. Fetches raw meter readings for all active contracts.
    2. Pro-rata interpolates readings to align with the 1st of each month.
    3. Stores InterpolatedReadings for the tenant dashboard.
    """
    result = asyncio.run(_run_daily_aggregator())
    return result


async def _run_daily_aggregator() -> dict:
    from datetime import datetime, timezone
    from sqlalchemy import select

    from app.core.database import AsyncSessionLocal
    from app.models.models import (
        Contract,
        ContractStatus,
        InterpolatedReading,
        Meter,
        MeterReading,
    )

    processed = 0
    async with AsyncSessionLocal() as db:
        # Fetch all active contracts
        contracts_result = await db.execute(
            select(Contract).where(Contract.status == ContractStatus.ACTIVE)
        )
        contracts = list(contracts_result.scalars().all())

        today = date.today()
        # Process the previous full month
        first_of_this_month = today.replace(day=1)
        period_end = first_of_this_month - timedelta(days=1)
        period_start = period_end.replace(day=1)

        for contract in contracts:
            meters_result = await db.execute(
                select(Meter).where(Meter.unit_id == contract.unit_id)
            )
            meters = list(meters_result.scalars().all())

            for meter in meters:
                try:
                    interp = await _interpolate_meter(db, meter.id, period_start, period_end)
                    if interp:
                        # Avoid duplicates
                        existing = await db.execute(
                            select(InterpolatedReading).where(
                                InterpolatedReading.meter_id == meter.id,
                                InterpolatedReading.period_start == period_start,
                                InterpolatedReading.period_end == period_end,
                            )
                        )
                        if not existing.scalar_one_or_none():
                            db.add(interp)
                            processed += 1
                except Exception:
                    logger.exception("Failed to interpolate meter %s", meter.id)

        await db.commit()

    return {"processed_meters": processed, "period_start": str(period_start), "period_end": str(period_end)}


async def _interpolate_meter(
    db: object,
    meter_id: str,
    period_start: date,
    period_end: date,
) -> object | None:
    """
    Pro-rata interpolation:
    Find the two readings bracketing the period and linearly interpolate
    to produce values exactly on period_start and period_end.
    """
    from sqlalchemy import select as _select
    from app.models.models import InterpolatedReading, MeterReading

    # Reading at or before period_start
    r_start_q = await db.execute(  # type: ignore[attr-defined]
        _select(MeterReading)
        .where(MeterReading.meter_id == meter_id, MeterReading.reading_date <= period_start)
        .order_by(MeterReading.reading_date.desc())
        .limit(1)
    )
    r_start = r_start_q.scalar_one_or_none()

    # Reading at or before period_end (latest)
    r_end_q = await db.execute(  # type: ignore[attr-defined]
        _select(MeterReading)
        .where(MeterReading.meter_id == meter_id, MeterReading.reading_date <= period_end)
        .order_by(MeterReading.reading_date.desc())
        .limit(1)
    )
    r_end = r_end_q.scalar_one_or_none()

    if not r_start or not r_end:
        return None

    # Pro-rata: if readings don't land exactly on period boundaries, interpolate
    v_start = _interpolate_value(r_start, r_end, period_start)
    v_end = _interpolate_value(r_start, r_end, period_end)
    consumption = max(v_end - v_start, Decimal("0"))

    return InterpolatedReading(
        meter_id=meter_id,
        period_start=period_start,
        period_end=period_end,
        value_start=v_start,
        value_end=v_end,
        consumption=consumption,
    )


def _interpolate_value(
    r_start: object,
    r_end: object,
    target_date: date,
) -> Decimal:
    """Linear interpolation between two meter readings."""
    d_start = r_start.reading_date  # type: ignore[attr-defined]
    d_end = r_end.reading_date  # type: ignore[attr-defined]
    v_start = Decimal(str(r_start.value))  # type: ignore[attr-defined]
    v_end = Decimal(str(r_end.value))  # type: ignore[attr-defined]

    if d_start == d_end:
        return v_start

    total_days = (d_end - d_start).days
    elapsed_days = (target_date - d_start).days
    fraction = Decimal(str(elapsed_days)) / Decimal(str(total_days))
    return v_start + (v_end - v_start) * fraction
