from datetime import date, datetime, timezone
from decimal import Decimal
import math
import uuid
from typing import Optional, List
from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import func

from app.database import get_db
from app.models.invoice import Invoice
from app.models.customer import Customer
from app.models.company import Company
from app.models.payment import Payment
from app.models.cash_transaction import CashTransaction
from app.schemas.invoice import (
    InvoiceResponse,
    InvoiceCreate,
    InvoiceUpdate,
    InvoiceDetailResponse,
)
from app.schemas.payment import (
    PaymentCreate,
    PaymentResponse,
    PaymentHistoryItem,
)
from app.schemas.common import PaginatedResponse
from app.services.invoice_status_service import calculate_invoice_financials

router = APIRouter(prefix="/invoices", tags=["Invoices"])
UNPROCESSABLE_STATUS = getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", 422)

def _to_invoice_response(inv: Invoice) -> InvoiceResponse:
    fin = calculate_invoice_financials(inv)
    return InvoiceResponse(
        invoice_id=inv.invoice_id,
        company_id=inv.company_id,
        customer_id=inv.customer_id,
        invoice_date=inv.invoice_date,
        due_date=inv.due_date,
        actual_payment_date=inv.actual_payment_date,
        payment_terms_days=inv.payment_terms_days,
        invoice_amount=inv.invoice_amount,
        currency=inv.currency,
        status=inv.status,
        historical_invoice_count=inv.historical_invoice_count,
        historical_late_rate=inv.historical_late_rate,
        amount_paid=fin["amount_paid"],
        outstanding_amount=fin["outstanding_amount"],
        payment_status=fin["payment_status"],
        due_status=fin["due_status"],
    )

@router.get("", response_model=PaginatedResponse[InvoiceResponse])
def list_invoices(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    customer_id: Optional[str] = Query(None, description="Filter by customer ID"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by invoice status (e.g. PAID, OPEN, CANCELLED)"),
    currency: Optional[str] = Query(None, description="Filter by currency code (e.g. INR, USD)"),
    invoice_date_from: Optional[date] = Query(None, description="Filter by invoice issue date from"),
    invoice_date_to: Optional[date] = Query(None, description="Filter by invoice issue date to"),
    due_date_from: Optional[date] = Query(None, description="Filter by due date from"),
    due_date_to: Optional[date] = Query(None, description="Filter by due date to"),
    payment_status: Optional[str] = Query(None, description="Filter by computed payment status (UNPAID, PARTIALLY_PAID, PAID)"),
    due_status: Optional[str] = Query(None, description="Filter by computed due status (SETTLED, OVERDUE, DUE_SOON, UPCOMING)"),
    db: Session = Depends(get_db),
):
    """Retrieve paginated invoices with optional filters and computed financial fields."""
    query = db.query(Invoice).options(selectinload(Invoice.payments))

    if customer_id:
        query = query.filter(Invoice.customer_id == customer_id.strip())
    if status_filter:
        query = query.filter(func.upper(Invoice.status) == status_filter.strip().upper())
    if currency:
        query = query.filter(func.upper(Invoice.currency) == currency.strip().upper())
    if invoice_date_from:
        query = query.filter(Invoice.invoice_date >= invoice_date_from)
    if invoice_date_to:
        query = query.filter(Invoice.invoice_date <= invoice_date_to)
    if due_date_from:
        query = query.filter(Invoice.due_date >= due_date_from)
    if due_date_to:
        query = query.filter(Invoice.due_date <= due_date_to)

    all_matches = query.order_by(Invoice.invoice_date.desc(), Invoice.invoice_id.asc()).all()

    # Apply computed status filters in memory if specified
    filtered = []
    for inv in all_matches:
        fin = calculate_invoice_financials(inv)
        if payment_status and fin["payment_status"] != payment_status.strip().upper():
            continue
        if due_status and fin["due_status"] != due_status.strip().upper():
            continue
        filtered.append((inv, fin))

    total = len(filtered)
    total_pages = math.ceil(total / page_size) if total > 0 else 0
    offset = (page - 1) * page_size
    page_items = filtered[offset : offset + page_size]

    response_items = [
        InvoiceResponse(
            invoice_id=inv.invoice_id,
            company_id=inv.company_id,
            customer_id=inv.customer_id,
            invoice_date=inv.invoice_date,
            due_date=inv.due_date,
            actual_payment_date=inv.actual_payment_date,
            payment_terms_days=inv.payment_terms_days,
            invoice_amount=inv.invoice_amount,
            currency=inv.currency,
            status=inv.status,
            historical_invoice_count=inv.historical_invoice_count,
            historical_late_rate=inv.historical_late_rate,
            amount_paid=fin["amount_paid"],
            outstanding_amount=fin["outstanding_amount"],
            payment_status=fin["payment_status"],
            due_status=fin["due_status"],
        )
        for inv, fin in page_items
    ]

    return PaginatedResponse(
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        items=response_items,
    )

@router.get("/{invoice_id}", response_model=InvoiceDetailResponse)
def get_invoice(invoice_id: str, db: Session = Depends(get_db)):
    """Retrieve detailed invoice view including customer info, payment history, and computed statuses."""
    invoice = (
        db.query(Invoice)
        .options(selectinload(Invoice.payments), selectinload(Invoice.customer))
        .filter(Invoice.invoice_id == invoice_id.strip())
        .first()
    )
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Invoice '{invoice_id}' not found",
        )

    fin = calculate_invoice_financials(invoice)
    cust_name = invoice.customer.customer_name if invoice.customer else None
    cust_country = invoice.customer.country if invoice.customer else None

    payment_responses = [
        PaymentResponse.model_validate(p) for p in (invoice.payments or [])
    ]

    return InvoiceDetailResponse(
        invoice_id=invoice.invoice_id,
        company_id=invoice.company_id,
        customer_id=invoice.customer_id,
        customer_name=cust_name,
        customer_country=cust_country,
        invoice_date=invoice.invoice_date,
        due_date=invoice.due_date,
        actual_payment_date=invoice.actual_payment_date,
        payment_terms_days=invoice.payment_terms_days,
        invoice_amount=invoice.invoice_amount,
        currency=invoice.currency,
        status=invoice.status,
        amount_paid=fin["amount_paid"],
        outstanding_amount=fin["outstanding_amount"],
        latest_payment_date=fin["latest_payment_date"],
        payment_status=fin["payment_status"],
        due_status=fin["due_status"],
        payments=payment_responses,
    )

@router.post("", response_model=InvoiceResponse, status_code=status.HTTP_201_CREATED)
def create_invoice(payload: InvoiceCreate, db: Session = Depends(get_db)):
    """Create a new invoice with full relationship and constraint validation."""
    # 1. Company check
    company = db.query(Company).filter(Company.company_id == payload.company_id.strip()).first()
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company '{payload.company_id}' not found",
        )

    # 2. Customer check
    customer = db.query(Customer).filter(Customer.customer_id == payload.customer_id.strip()).first()
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer '{payload.customer_id}' not found",
        )

    # 3. Cross-company check
    if customer.company_id != payload.company_id.strip():
        raise HTTPException(
            status_code=UNPROCESSABLE_STATUS,
            detail=f"Customer '{payload.customer_id}' does not belong to company '{payload.company_id}'",
        )

    # 4. Amount validation
    if payload.invoice_amount <= Decimal("0.00"):
        raise HTTPException(
            status_code=UNPROCESSABLE_STATUS,
            detail="Invoice amount must be greater than zero",
        )

    # 5. Due date cannot precede invoice date
    if payload.due_date < payload.invoice_date:
        raise HTTPException(
            status_code=UNPROCESSABLE_STATUS,
            detail="Due date cannot precede invoice issue date",
        )

    # 6. Currency format
    curr = payload.currency.strip().upper()

    # 7. Invoice ID generation / uniqueness check
    if payload.invoice_id and payload.invoice_id.strip():
        inv_id = payload.invoice_id.strip()
        existing = db.query(Invoice).filter(Invoice.invoice_id == inv_id).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Invoice ID '{inv_id}' already exists",
            )
    else:
        count = db.query(func.count(Invoice.invoice_id)).scalar() or 0
        inv_id = f"INV-{count + 1:06d}"
        if db.query(Invoice).filter(Invoice.invoice_id == inv_id).first():
            inv_id = f"INV-{uuid.uuid4().hex[:8].upper()}"

    invoice = Invoice(
        invoice_id=inv_id,
        company_id=payload.company_id.strip(),
        customer_id=payload.customer_id.strip(),
        invoice_date=payload.invoice_date,
        due_date=payload.due_date,
        actual_payment_date=None,
        payment_terms_days=payload.payment_terms_days,
        invoice_amount=payload.invoice_amount,
        currency=curr,
        status="OPEN",
        historical_invoice_count=0,
        historical_late_rate=Decimal("0.0"),
    )
    db.add(invoice)
    db.commit()
    db.refresh(invoice)
    return _to_invoice_response(invoice)

@router.patch("/{invoice_id}", response_model=InvoiceResponse)
def update_invoice(invoice_id: str, payload: InvoiceUpdate, db: Session = Depends(get_db)):
    """Safely update editable invoice attributes with strict payment-protection rules."""
    invoice = (
        db.query(Invoice)
        .options(selectinload(Invoice.payments))
        .filter(Invoice.invoice_id == invoice_id.strip())
        .first()
    )
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Invoice '{invoice_id}' not found",
        )

    fin = calculate_invoice_financials(invoice)
    amount_paid = fin["amount_paid"]
    has_payments = amount_paid > Decimal("0.00")

    # 1. Invoice amount update rule: cannot be less than already received payment total
    if payload.invoice_amount is not None:
        if payload.invoice_amount <= Decimal("0.00"):
            raise HTTPException(
                status_code=UNPROCESSABLE_STATUS,
                detail="Invoice amount must be greater than zero",
            )
        if payload.invoice_amount < amount_paid:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Cannot reduce invoice amount to {payload.invoice_amount} below received payments total of {amount_paid}",
            )
        invoice.invoice_amount = payload.invoice_amount

    # 2. Currency update rule: cannot be changed if payments recorded
    if payload.currency is not None:
        new_curr = payload.currency.strip().upper()
        if new_curr != invoice.currency:
            if has_payments:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Cannot change invoice currency after payments have been recorded",
                )
            invoice.currency = new_curr

    # 3. Customer reassignment rule: not permitted after payments recorded
    if payload.customer_id is not None:
        new_cust_id = payload.customer_id.strip()
        if new_cust_id != invoice.customer_id:
            if has_payments:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Cannot reassign invoice customer after payments have been recorded",
                )
            customer = db.query(Customer).filter(Customer.customer_id == new_cust_id).first()
            if not customer:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Customer '{new_cust_id}' not found",
                )
            if customer.company_id != invoice.company_id:
                raise HTTPException(
                    status_code=UNPROCESSABLE_STATUS,
                    detail=f"Customer '{new_cust_id}' does not belong to company '{invoice.company_id}'",
                )
            invoice.customer_id = new_cust_id

    # 4. Dates validation
    new_inv_date = payload.invoice_date or invoice.invoice_date
    new_due_date = payload.due_date or invoice.due_date
    if new_due_date < new_inv_date:
        raise HTTPException(
            status_code=UNPROCESSABLE_STATUS,
            detail="Due date cannot precede invoice issue date",
        )
    invoice.invoice_date = new_inv_date
    invoice.due_date = new_due_date

    if payload.payment_terms_days is not None:
        invoice.payment_terms_days = payload.payment_terms_days

    db.commit()
    db.refresh(invoice)
    return _to_invoice_response(invoice)

@router.post("/{invoice_id}/cancel")
def cancel_invoice(invoice_id: str, db: Session = Depends(get_db)):
    """Cancel an invoice if and only if zero payments have been received."""
    invoice = (
        db.query(Invoice)
        .options(selectinload(Invoice.payments))
        .filter(Invoice.invoice_id == invoice_id.strip())
        .first()
    )
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Invoice '{invoice_id}' not found",
        )

    fin = calculate_invoice_financials(invoice)
    if fin["amount_paid"] > Decimal("0.00"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot cancel invoice '{invoice_id}' with existing recorded payments totaling {fin['amount_paid']}",
        )

    invoice.status = "CANCELLED"
    db.commit()
    return {"message": "Invoice cancelled successfully", "invoice_id": invoice_id, "status": "CANCELLED"}

@router.post("/{invoice_id}/payments", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
def record_payment(
    invoice_id: str,
    payload: PaymentCreate,
    idempotency_key: str = Header(..., alias="Idempotency-Key", description="Unique request idempotency key"),
    db: Session = Depends(get_db),
):
    """
    Atomically record a payment against an invoice and generate the matching cash transaction.
    Enforces idempotency, overpayment prevention, currency matching, and date consistency.
    """
    key = idempotency_key.strip()
    if not key:
        raise HTTPException(
            status_code=UNPROCESSABLE_STATUS,
            detail="Idempotency-Key header cannot be empty",
        )

    # 1. Check idempotency key in payments table
    existing_payment = db.query(Payment).filter(Payment.idempotency_key == key).first()
    if existing_payment:
        # Check payload equality
        if (
            existing_payment.invoice_id == invoice_id.strip()
            and abs(existing_payment.amount - payload.amount) < Decimal("0.001")
            and existing_payment.currency == payload.currency.strip().upper()
            and existing_payment.payment_date == payload.payment_date
        ):
            # Idempotent replay: return existing payment
            return existing_payment
        else:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Idempotency-Key '{key}' was already used with a different request payload",
            )

    # 2. Invoice validation
    invoice = (
        db.query(Invoice)
        .options(selectinload(Invoice.payments))
        .filter(Invoice.invoice_id == invoice_id.strip())
        .first()
    )
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Invoice '{invoice_id}' not found",
        )

    # Invoice cancellation check
    if invoice.status.upper() == "CANCELLED":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot record payment on cancelled invoice '{invoice_id}'",
        )

    # 3. Currency match
    curr = payload.currency.strip().upper()
    if curr != invoice.currency:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Payment currency '{curr}' does not match invoice currency '{invoice.currency}'",
        )

    # 4. Amount validation
    if payload.amount <= Decimal("0.00"):
        raise HTTPException(
            status_code=UNPROCESSABLE_STATUS,
            detail="Payment amount must be greater than zero",
        )

    fin = calculate_invoice_financials(invoice)
    outstanding = fin["outstanding_amount"]
    if payload.amount > outstanding:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Payment amount {payload.amount} exceeds invoice outstanding balance of {outstanding}",
        )

    # 5. Date validations
    if payload.payment_date < invoice.invoice_date:
        raise HTTPException(
            status_code=UNPROCESSABLE_STATUS,
            detail=f"Payment date {payload.payment_date} cannot precede invoice issue date {invoice.invoice_date}",
        )

    today = date.today()
    if payload.payment_date > today:
        raise HTTPException(
            status_code=UNPROCESSABLE_STATUS,
            detail=f"Payment date {payload.payment_date} cannot be in the future for a completed payment",
        )

    # 6. Atomic creation of CashTransaction and Payment
    try:
        txn_id = f"TXN-IN-{uuid.uuid4().hex[:10].upper()}"
        payment_id = f"PAY-{uuid.uuid4().hex[:10].upper()}"

        description = (
            payload.notes
            or f"Payment received for invoice {invoice.invoice_id} ({invoice.customer_id})"
        )

        cash_txn = CashTransaction(
            transaction_id=txn_id,
            company_id=invoice.company_id,
            transaction_date=payload.payment_date,
            transaction_type="INFLOW",
            category="CUSTOMER_PAYMENT",
            amount=payload.amount,
            currency=curr,
            linked_invoice_id=invoice.invoice_id,
            counterparty_id=invoice.customer_id,
            description=description,
        )
        db.add(cash_txn)
        db.flush()

        payment = Payment(
            payment_id=payment_id,
            company_id=invoice.company_id,
            invoice_id=invoice.invoice_id,
            payment_date=payload.payment_date,
            amount=payload.amount,
            currency=curr,
            payment_method=payload.payment_method,
            reference_number=payload.reference_number,
            notes=payload.notes,
            cash_transaction_id=txn_id,
            idempotency_key=key,
            source="MANUAL",
            created_at=datetime.now(timezone.utc),
        )
        db.add(payment)

        # Update invoice state if fully settled
        new_paid = fin["amount_paid"] + payload.amount
        if abs(invoice.invoice_amount - new_paid) < Decimal("0.005"):
            invoice.status = "PAID"
            invoice.actual_payment_date = payload.payment_date

        db.commit()
        db.refresh(payment)
        return payment

    except Exception:
        db.rollback()
        raise

@router.get("/{invoice_id}/payments", response_model=List[PaymentHistoryItem])
def get_invoice_payments(invoice_id: str, db: Session = Depends(get_db)):
    """Retrieve all payments for an invoice in chronological order."""
    invoice = db.query(Invoice).filter(Invoice.invoice_id == invoice_id.strip()).first()
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Invoice '{invoice_id}' not found",
        )

    payments = (
        db.query(Payment)
        .filter(Payment.invoice_id == invoice_id.strip())
        .order_by(Payment.payment_date.asc(), Payment.created_at.asc())
        .all()
    )
    return payments
