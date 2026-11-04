from datetime import date
import math
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import func

from app.database import get_db
from app.models.payment import Payment
from app.models.invoice import Invoice
from app.schemas.payment import PaymentResponse, PaymentDetailResponse
from app.schemas.common import PaginatedResponse

router = APIRouter(prefix="/payments", tags=["Payments"])

@router.get("", response_model=PaginatedResponse[PaymentResponse])
def list_payments(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    invoice_id: Optional[str] = Query(None, description="Filter by invoice ID"),
    customer_id: Optional[str] = Query(None, description="Filter by customer ID via linked invoice"),
    start_date: Optional[date] = Query(None, description="Filter payments on or after date"),
    end_date: Optional[date] = Query(None, description="Filter payments on or before date"),
    currency: Optional[str] = Query(None, description="Filter by currency code"),
    db: Session = Depends(get_db),
):
    """Retrieve paginated payments with optional filters."""
    query = db.query(Payment)

    if invoice_id:
        query = query.filter(Payment.invoice_id == invoice_id.strip())
    if customer_id:
        query = query.join(Invoice, Payment.invoice_id == Invoice.invoice_id).filter(
            Invoice.customer_id == customer_id.strip()
        )
    if start_date:
        query = query.filter(Payment.payment_date >= start_date)
    if end_date:
        query = query.filter(Payment.payment_date <= end_date)
    if currency:
        query = query.filter(func.upper(Payment.currency) == currency.strip().upper())

    total = query.with_entities(func.count(Payment.payment_id)).scalar() or 0
    total_pages = math.ceil(total / page_size) if total > 0 else 0
    offset = (page - 1) * page_size

    payments = (
        query.order_by(Payment.payment_date.desc(), Payment.created_at.desc())
        .offset(offset)
        .limit(page_size)
        .all()
    )

    return PaginatedResponse(
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        items=payments,
    )

@router.get("/{payment_id}", response_model=PaymentDetailResponse)
def get_payment(payment_id: str, db: Session = Depends(get_db)):
    """Retrieve a single payment record with invoice summary."""
    payment = (
        db.query(Payment)
        .options(selectinload(Payment.invoice))
        .filter(Payment.payment_id == payment_id.strip())
        .first()
    )
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Payment '{payment_id}' not found",
        )

    inv = payment.invoice
    inv_amount = inv.invoice_amount if inv else payment.amount
    inv_status = inv.status if inv else "UNKNOWN"

    return PaymentDetailResponse(
        payment=PaymentResponse.model_validate(payment),
        invoice_id=payment.invoice_id,
        invoice_amount=inv_amount,
        invoice_status=inv_status,
    )
