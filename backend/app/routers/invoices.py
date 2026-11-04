import math
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models.invoice import Invoice
from app.schemas.invoice import InvoiceResponse
from app.schemas.common import PaginatedResponse

router = APIRouter(prefix="/invoices", tags=["Invoices"])

@router.get("", response_model=PaginatedResponse[InvoiceResponse])
def list_invoices(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    customer_id: Optional[str] = Query(None, description="Filter by customer ID"),
    status: Optional[str] = Query(None, description="Filter by invoice status (e.g. PAID, OPEN)"),
    currency: Optional[str] = Query(None, description="Filter by currency code (e.g. INR, USD)"),
    db: Session = Depends(get_db),
):
    """Retrieve paginated invoices with optional filters."""
    query = db.query(Invoice)

    if customer_id:
        query = query.filter(Invoice.customer_id == customer_id.strip())
    if status:
        query = query.filter(func.upper(Invoice.status) == status.strip().upper())
    if currency:
        query = query.filter(func.upper(Invoice.currency) == currency.strip().upper())

    total = query.with_entities(func.count(Invoice.invoice_id)).scalar() or 0
    total_pages = math.ceil(total / page_size) if total > 0 else 0
    offset = (page - 1) * page_size

    invoices = (
        query.order_by(Invoice.invoice_date.desc(), Invoice.invoice_id.asc())
        .offset(offset)
        .limit(page_size)
        .all()
    )

    return PaginatedResponse(
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        items=invoices,
    )

