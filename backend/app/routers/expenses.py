import math
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import List, Optional
from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import func

from app.database import get_db
from app.models.expense import Expense
from app.models.expense_payment import ExpensePayment
from app.models.cash_transaction import CashTransaction
from app.schemas.expense import (
    ExpenseResponse,
    ExpenseDetailResponse,
    ExpensePaymentCreate,
    ExpensePaymentResponse,
)
from app.schemas.common import PaginatedResponse

router = APIRouter(prefix="/expenses", tags=["Expenses"])


def _format_expense_response(exp: Expense) -> ExpenseResponse:
    """Format expense with computed outstanding amount and payment status."""
    tot = Decimal(str(exp.amount)) if exp.amount is not None else Decimal("0.00")
    paid = Decimal(str(exp.amount_paid)) if exp.amount_paid is not None else Decimal("0.00")
    outstanding = max(Decimal("0.00"), tot - paid)
    status_str = "PAID" if paid >= tot and tot > 0 else ("PARTIALLY_PAID" if paid > 0 else "UNPAID")

    return ExpenseResponse(
        expense_id=exp.expense_id,
        company_id=exp.company_id,
        expense_date=exp.expense_date,
        due_date=exp.due_date,
        actual_payment_date=exp.actual_payment_date,
        category=exp.category,
        amount=tot,
        amount_paid=paid,
        currency=exp.currency,
        status=exp.status,
        linked_invoice_id=exp.linked_invoice_id,
        outstanding_amount=outstanding,
        payment_status=status_str,
    )


@router.get("", response_model=PaginatedResponse[ExpenseResponse])
def list_expenses(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    category: Optional[str] = Query(None, description="Filter by expense category"),
    status: Optional[str] = Query(None, description="Filter by status (OPEN, PAID, PARTIALLY_PAID)"),
    company_id: Optional[str] = Query("FINORA_DEMO", description="Company ID"),
    db: Session = Depends(get_db),
):
    """Retrieve paginated expenses with optional category and status filters."""
    query = db.query(Expense).filter(Expense.company_id == company_id)

    if category:
        query = query.filter(func.upper(Expense.category) == category.strip().upper())
    if status:
        query = query.filter(func.upper(Expense.status) == status.strip().upper())

    total = query.with_entities(func.count(Expense.expense_id)).scalar() or 0
    total_pages = math.ceil(total / page_size) if total > 0 else 0
    offset = (page - 1) * page_size

    expenses = (
        query.order_by(Expense.due_date.asc(), Expense.expense_date.desc(), Expense.expense_id.asc())
        .offset(offset)
        .limit(page_size)
        .all()
    )

    items = [_format_expense_response(e) for e in expenses]

    return PaginatedResponse(
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        items=items,
    )


@router.get("/{expense_id}", response_model=ExpenseDetailResponse)
def get_expense(expense_id: str, db: Session = Depends(get_db)):
    """Retrieve a single expense with its payment history."""
    expense = (
        db.query(Expense)
        .options(selectinload(Expense.payments))
        .filter(Expense.expense_id == expense_id.strip())
        .first()
    )
    if not expense:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Expense '{expense_id}' not found.",
        )

    base = _format_expense_response(expense)
    payments = [ExpensePaymentResponse.model_validate(p) for p in (expense.payments or [])]

    return ExpenseDetailResponse(
        **base.model_dump(),
        payments=payments,
    )


@router.post("/{expense_id}/payments", response_model=ExpensePaymentResponse, status_code=status.HTTP_201_CREATED)
def record_expense_payment(
    expense_id: str,
    payload: ExpensePaymentCreate,
    idempotency_key: str = Header(..., alias="Idempotency-Key", description="Unique request idempotency key"),
    db: Session = Depends(get_db),
):
    """
    Atomically record a disbursement payment against an existing expense
    and create the corresponding actual OUTFLOW cash transaction.
    Enforces idempotency, overpayment prevention, currency matching, and date consistency.
    """
    key = idempotency_key.strip()
    if not key:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Idempotency-Key header cannot be empty.",
        )

    # 1. Idempotency check in expense_payments
    existing_payment = db.query(ExpensePayment).filter(ExpensePayment.idempotency_key == key).first()
    if existing_payment:
        if (
            existing_payment.expense_id == expense_id.strip()
            and abs(existing_payment.amount - payload.amount) < Decimal("0.005")
            and existing_payment.payment_date == payload.payment_date
        ):
            return existing_payment
        else:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Idempotency-Key '{key}' was already used with a different request payload.",
            )

    # 2. Expense check
    expense = (
        db.query(Expense)
        .options(selectinload(Expense.payments))
        .filter(Expense.expense_id == expense_id.strip())
        .first()
    )
    if not expense:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Expense '{expense_id}' not found.",
        )

    # 3. Currency check
    curr = (payload.currency or expense.currency).strip().upper()
    if curr != expense.currency.strip().upper():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Payment currency '{curr}' does not match expense currency '{expense.currency}'.",
        )

    # 4. Amount validation against remaining balance
    if payload.amount <= Decimal("0.00"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Payment amount must be greater than zero.",
        )

    tot = Decimal(str(expense.amount))
    paid = Decimal(str(expense.amount_paid or 0))
    outstanding = max(Decimal("0.00"), tot - paid)

    if payload.amount > outstanding:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Payment amount ({payload.amount}) exceeds remaining payable balance of {outstanding} {expense.currency}.",
        )

    # 5. Date validation
    if payload.payment_date < expense.expense_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Payment date {payload.payment_date} cannot precede expense date {expense.expense_date}.",
        )

    today = date.today()
    if payload.payment_date > today:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Payment date {payload.payment_date} cannot be in the future for an actual completed payment.",
        )

    # 6. Atomic creation of CashTransaction (OUTFLOW) and ExpensePayment
    try:
        txn_id = f"TXN-OUT-{uuid.uuid4().hex[:10].upper()}"
        payment_id = f"EXP-PAY-{uuid.uuid4().hex[:10].upper()}"

        description = (
            payload.notes
            or f"Disbursement for {expense.category} expense {expense.expense_id}"
        )

        cash_txn = CashTransaction(
            transaction_id=txn_id,
            company_id=expense.company_id,
            transaction_date=payload.payment_date,
            transaction_type="OUTFLOW",
            category=expense.category,
            amount=payload.amount,
            currency=curr,
            linked_expense_id=expense.expense_id,
            linked_invoice_id=expense.linked_invoice_id,
            counterparty_id=f"VENDOR_{expense.category}",
            description=description,
        )
        db.add(cash_txn)
        db.flush()

        payment = ExpensePayment(
            payment_id=payment_id,
            company_id=expense.company_id,
            expense_id=expense.expense_id,
            payment_date=payload.payment_date,
            amount=payload.amount,
            currency=curr,
            payment_method=payload.payment_method,
            reference_number=payload.reference_number,
            notes=payload.notes,
            cash_transaction_id=txn_id,
            idempotency_key=key,
            created_at=datetime.now(timezone.utc),
        )
        db.add(payment)

        # Update expense state
        new_paid = (paid + payload.amount).quantize(Decimal("0.01"))
        expense.amount_paid = new_paid
        expense.actual_payment_date = payload.payment_date
        if abs(tot - new_paid) < Decimal("0.005"):
            expense.status = "PAID"
        else:
            expense.status = "PARTIALLY_PAID"

        db.commit()
        db.refresh(payment)
        return payment

    except Exception:
        db.rollback()
        raise


@router.get("/{expense_id}/payments", response_model=List[ExpensePaymentResponse])
def get_expense_payments(expense_id: str, db: Session = Depends(get_db)):
    """Retrieve all payments recorded against an expense."""
    expense = db.query(Expense).filter(Expense.expense_id == expense_id.strip()).first()
    if not expense:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Expense '{expense_id}' not found.",
        )

    payments = (
        db.query(ExpensePayment)
        .filter(ExpensePayment.expense_id == expense_id.strip())
        .order_by(ExpensePayment.payment_date.desc(), ExpensePayment.created_at.desc())
        .all()
    )
    return payments
