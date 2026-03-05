"""Billing routes – graph execution and PDF generation trigger."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_db, require_landlord
from app.models.models import Contract, Property, Unit, User, UtilityBill, UtilityBillStatus
from app.models.schemas import BillingGraph, GraphCalculationResult, UtilityBillRead
from app.services.graph_engine import GraphEngine

router = APIRouter(prefix="/billing", tags=["billing"])


@router.post("/calculate-graph", response_model=GraphCalculationResult)
async def calculate_graph(
    payload: BillingGraph,
    bill_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_landlord),
) -> GraphCalculationResult:
    """
    Execute a node-based billing graph (DAG).

    - In **preview_mode** the graph is run with sample_data and results are not persisted.
    - Otherwise the graph is executed against real meter readings and results are stored
      as BillLineItems on the given ``bill_id``.
    """
    if bill_id and not payload.preview_mode:
        # Verify landlord owns the bill
        bill = await _get_owned_bill(db, bill_id, current_user.id)

    engine = GraphEngine(db)
    result = await engine.execute(payload, bill_id=bill_id if not payload.preview_mode else None)

    if result.errors and not payload.preview_mode:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"message": "Graph execution failed", "errors": result.errors},
        )

    # Store calculation trace in the bill
    if bill_id and not payload.preview_mode and not result.errors:
        bill_result = await db.execute(
            select(UtilityBill).where(UtilityBill.id == bill_id)
        )
        bill_obj = bill_result.scalar_one_or_none()
        if bill_obj:
            bill_obj.calculation_trace = result.calculation_trace
            await db.flush()

    return result


@router.get("/utility-bills/{bill_id}", response_model=UtilityBillRead)
async def get_bill(
    bill_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_landlord),
) -> UtilityBill:
    result = await db.execute(
        select(UtilityBill)
        .options(selectinload(UtilityBill.line_items))
        .join(Contract, UtilityBill.contract_id == Contract.id)
        .join(Unit, Contract.unit_id == Unit.id)
        .join(Property, Unit.property_id == Property.id)
        .where(UtilityBill.id == bill_id, Property.landlord_id == current_user.id)
    )
    bill = result.scalar_one_or_none()
    if not bill:
        raise HTTPException(status_code=404, detail="Utility bill not found")
    return bill


@router.post("/utility-bills/{bill_id}/generate-pdf", status_code=status.HTTP_202_ACCEPTED)
async def generate_pdf(
    bill_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_landlord),
) -> dict:
    """Enqueue a Celery task to generate the PDF for this utility bill."""
    await _get_owned_bill(db, bill_id, current_user.id)

    from app.worker.tasks import generate_bill_pdf  # lazy import to avoid circular deps

    task = generate_bill_pdf.delay(bill_id)
    return {"task_id": task.id, "status": "queued"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


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
