"""
Service layer for Cash Flow Data Foundation (Phase 4 Stage 4A).

Handles Cash Balance Snapshots, Collection Forecast Overrides,
and Expense Forecast Assumptions.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any, List, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.models.company import Company
from app.models.invoice import Invoice
from app.models.cash_balance_snapshot import CashBalanceSnapshot
from app.models.collection_forecast_override import CollectionForecastOverride
from app.models.expense_forecast_assumption import ExpenseForecastAssumption
from app.schemas.cashflow_forecast import (
    CashBalanceSnapshotCreate,
    CashBalanceSnapshotUpdate,
    CollectionOverrideCreate,
    ExpenseAssumptionCreate,
    ExpenseAssumptionUpdate,
)


def record_cash_position(
    db: Session,
    payload: CashBalanceSnapshotCreate,
) -> CashBalanceSnapshot:
    """Record an opening cash balance snapshot for a company and date."""
    company = db.query(Company).filter(Company.company_id == payload.company_id).first()
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company '{payload.company_id}' not found.",
        )

    # Check for existing snapshot on same company, date, and currency
    existing = (
        db.query(CashBalanceSnapshot)
        .filter(
            CashBalanceSnapshot.company_id == payload.company_id,
            CashBalanceSnapshot.as_of_date == payload.as_of_date,
            CashBalanceSnapshot.currency == payload.currency,
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Cash balance snapshot already exists for company '{payload.company_id}' "
                f"on date '{payload.as_of_date}' in currency '{payload.currency}' (snapshot_id={existing.snapshot_id})."
            ),
        )

    snapshot_id = f"SNP-{uuid.uuid4().hex[:12].upper()}"
    snapshot = CashBalanceSnapshot(
        snapshot_id=snapshot_id,
        company_id=payload.company_id,
        as_of_date=payload.as_of_date,
        balance_amount=payload.balance_amount,
        currency=payload.currency,
        minimum_cash_threshold=payload.minimum_cash_threshold,
        source=payload.source,
        notes=payload.notes,
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    return snapshot


def update_cash_position(
    db: Session,
    snapshot_id: str,
    payload: CashBalanceSnapshotUpdate,
) -> CashBalanceSnapshot:
    """Update an existing cash balance snapshot with audit trails and validation."""
    snapshot = (
        db.query(CashBalanceSnapshot)
        .filter(CashBalanceSnapshot.snapshot_id == snapshot_id)
        .first()
    )
    if not snapshot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cash balance snapshot '{snapshot_id}' not found.",
        )

    # Check if as_of_date is changing and would conflict with another existing snapshot
    if payload.as_of_date and payload.as_of_date != snapshot.as_of_date:
        existing = (
            db.query(CashBalanceSnapshot)
            .filter(
                CashBalanceSnapshot.company_id == snapshot.company_id,
                CashBalanceSnapshot.as_of_date == payload.as_of_date,
                CashBalanceSnapshot.currency == snapshot.currency,
                CashBalanceSnapshot.snapshot_id != snapshot_id,
            )
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Another snapshot already exists for company '{snapshot.company_id}' "
                    f"on date '{payload.as_of_date}' in currency '{snapshot.currency}' (snapshot_id={existing.snapshot_id})."
                ),
            )

    # Audit tracking
    audit_changes = []
    if payload.balance_amount is not None and payload.balance_amount != snapshot.balance_amount:
        audit_changes.append(f"balance: {snapshot.balance_amount} -> {payload.balance_amount}")
        snapshot.balance_amount = payload.balance_amount

    if payload.minimum_cash_threshold is not None and payload.minimum_cash_threshold != snapshot.minimum_cash_threshold:
        audit_changes.append(f"threshold: {snapshot.minimum_cash_threshold} -> {payload.minimum_cash_threshold}")
        snapshot.minimum_cash_threshold = payload.minimum_cash_threshold

    if payload.as_of_date is not None and payload.as_of_date != snapshot.as_of_date:
        audit_changes.append(f"as_of_date: {snapshot.as_of_date} -> {payload.as_of_date}")
        snapshot.as_of_date = payload.as_of_date

    if audit_changes:
        timestamp_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        reason_str = f" Reason: {payload.notes}" if payload.notes else ""
        audit_entry = f"[Updated {timestamp_str}: {', '.join(audit_changes)}.{reason_str}]"

        if snapshot.notes:
            snapshot.notes = f"{snapshot.notes}\n{audit_entry}"
        else:
            snapshot.notes = audit_entry
    elif payload.notes:
        snapshot.notes = (
            f"{snapshot.notes}\n[Note {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}]: {payload.notes}"
            if snapshot.notes
            else payload.notes
        )

    snapshot.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(snapshot)
    return snapshot


def get_latest_cash_position(
    db: Session,
    company_id: str,
    as_of_date: Optional[date] = None,
    currency: str = "INR",
) -> Optional[CashBalanceSnapshot]:
    """Retrieve the latest cash balance snapshot applicable for the given date."""
    company = db.query(Company).filter(Company.company_id == company_id).first()
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company '{company_id}' not found.",
        )

    query = db.query(CashBalanceSnapshot).filter(
        CashBalanceSnapshot.company_id == company_id,
        CashBalanceSnapshot.currency == currency,
    )
    if as_of_date:
        query = query.filter(CashBalanceSnapshot.as_of_date <= as_of_date)

    return (
        query.order_by(
            CashBalanceSnapshot.as_of_date.desc(),
            CashBalanceSnapshot.created_at.desc(),
        )
        .first()
    )


def create_collection_override(
    db: Session,
    payload: CollectionOverrideCreate,
) -> CollectionForecastOverride:
    """
    Create a manual customer commitment / collection forecast override for an invoice.
    Supports partial commitments, probability weighting, and validates against outstanding balance.
    """
    company = db.query(Company).filter(Company.company_id == payload.company_id).first()
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company '{payload.company_id}' not found.",
        )

    invoice = db.query(Invoice).filter(Invoice.invoice_id == payload.invoice_id).first()
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Invoice '{payload.invoice_id}' not found.",
        )

    # Calculate current invoice financials
    total_amount = Decimal(str(invoice.invoice_amount))
    payments = invoice.payments or []
    amount_paid = sum((Decimal(str(p.amount)) for p in payments), Decimal("0.00"))
    outstanding = max(Decimal("0.00"), total_amount - amount_paid)

    if str(invoice.status).upper() in ("PAID", "CANCELLED") or outstanding <= Decimal("0.00"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Cannot add collection commitment for invoice '{invoice.invoice_id}' with status '{invoice.status}' and zero outstanding balance.",
        )

    # Check existing active commitments for this invoice
    active_commitments = (
        db.query(CollectionForecastOverride)
        .filter(
            CollectionForecastOverride.invoice_id == payload.invoice_id,
            CollectionForecastOverride.is_active == True,
        )
        .all()
    )

    current_committed = sum(
        (Decimal(str(c.expected_amount)) if c.expected_amount is not None else outstanding for c in active_commitments),
        Decimal("0.00"),
    )

    # Determine expected amount (default to remaining uncommitted balance)
    if payload.expected_amount is not None:
        amt = Decimal(str(payload.expected_amount)).quantize(Decimal("0.01"))
        if amt <= Decimal("0.00"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Expected collection amount must be greater than zero.",
            )
    else:
        amt = max(Decimal("0.00"), outstanding - current_committed).quantize(Decimal("0.01"))
        if amt <= Decimal("0.00"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invoice '{invoice.invoice_id}' already has active commitments covering the full outstanding balance of {outstanding}.",
            )

    # Validate amount against remaining outstanding balance
    if current_committed + amt > outstanding:
        remaining_allocatable = max(Decimal("0.00"), outstanding - current_committed)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Total active commitment amount ({current_committed + amt}) exceeds "
                f"remaining invoice outstanding balance ({outstanding}). "
                f"Maximum available for commitment: {remaining_allocatable} {invoice.currency}."
            ),
        )

    # Prevent duplicate active commitments on the exact same date and amount
    for existing in active_commitments:
        if existing.expected_collection_date == payload.expected_collection_date:
            ex_amt = Decimal(str(existing.expected_amount)) if existing.expected_amount is not None else outstanding
            if abs(ex_amt - amt) < Decimal("0.01"):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"An active commitment for invoice '{payload.invoice_id}' with date '{payload.expected_collection_date}' and amount {amt} already exists.",
                )

    # Normalize probability (accepts 0.0 - 1.0 or 1 - 100)
    raw_prob = Decimal(str(payload.recovery_probability)) if payload.recovery_probability is not None else Decimal("1.00")
    if raw_prob > Decimal("1.00") and raw_prob <= Decimal("100.00"):
        prob = (raw_prob / Decimal("100.00")).quantize(Decimal("0.0001"))
    else:
        prob = raw_prob.quantize(Decimal("0.0001"))

    if prob <= Decimal("0.00") or prob > Decimal("1.00"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Recovery probability must be between 0.01 and 1.00 (or 1% to 100%).",
        )

    override_id = f"OVR-{uuid.uuid4().hex[:12].upper()}"
    override = CollectionForecastOverride(
        override_id=override_id,
        company_id=payload.company_id,
        invoice_id=payload.invoice_id,
        expected_collection_date=payload.expected_collection_date,
        expected_amount=amt,
        recovery_probability=prob,
        commitment_source=payload.commitment_source or "CUSTOMER_COMMITMENT",
        notes=payload.notes,
        is_active=payload.is_active,
    )
    db.add(override)
    db.commit()
    db.refresh(override)
    return override


def update_collection_override(
    db: Session,
    override_id: str,
    payload: Any,
) -> CollectionForecastOverride:
    """Update an existing collection commitment / forecast override."""
    override = (
        db.query(CollectionForecastOverride)
        .filter(CollectionForecastOverride.override_id == override_id)
        .first()
    )
    if not override:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Collection override '{override_id}' not found.",
        )

    invoice = db.query(Invoice).filter(Invoice.invoice_id == override.invoice_id).first()
    if invoice and payload.expected_amount is not None:
        total_amount = Decimal(str(invoice.invoice_amount))
        payments = invoice.payments or []
        amount_paid = sum((Decimal(str(p.amount)) for p in payments), Decimal("0.00"))
        outstanding = max(Decimal("0.00"), total_amount - amount_paid)

        # Other active commitments excluding this one
        other_commitments = (
            db.query(CollectionForecastOverride)
            .filter(
                CollectionForecastOverride.invoice_id == override.invoice_id,
                CollectionForecastOverride.override_id != override_id,
                CollectionForecastOverride.is_active == True,
            )
            .all()
        )
        other_total = sum(
            (Decimal(str(c.expected_amount)) if c.expected_amount is not None else outstanding for c in other_commitments),
            Decimal("0.00"),
        )
        new_amt = Decimal(str(payload.expected_amount)).quantize(Decimal("0.01"))
        if other_total + new_amt > outstanding:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Updated commitment amount ({new_amt}) causes total active commitments ({other_total + new_amt}) to exceed outstanding balance ({outstanding}).",
            )
        override.expected_amount = new_amt

    if payload.expected_collection_date is not None:
        override.expected_collection_date = payload.expected_collection_date

    if payload.recovery_probability is not None:
        raw_prob = Decimal(str(payload.recovery_probability))
        if raw_prob > Decimal("1.00") and raw_prob <= Decimal("100.00"):
            prob = (raw_prob / Decimal("100.00")).quantize(Decimal("0.0001"))
        else:
            prob = raw_prob.quantize(Decimal("0.0001"))
        if prob <= Decimal("0.00") or prob > Decimal("1.00"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Recovery probability must be between 0.01 and 1.00.",
            )
        override.recovery_probability = prob

    if payload.commitment_source is not None:
        override.commitment_source = payload.commitment_source

    if payload.notes is not None:
        override.notes = payload.notes

    if payload.is_active is not None:
        override.is_active = payload.is_active

    db.commit()
    db.refresh(override)
    return override


def list_collection_overrides(
    db: Session,
    company_id: str,
    invoice_id: Optional[str] = None,
    is_active: Optional[bool] = None,
) -> List[CollectionForecastOverride]:
    """Retrieve collection overrides for a company."""
    query = db.query(CollectionForecastOverride).filter(
        CollectionForecastOverride.company_id == company_id
    )
    if invoice_id:
        query = query.filter(CollectionForecastOverride.invoice_id == invoice_id)
    if is_active is not None:
        query = query.filter(CollectionForecastOverride.is_active == is_active)

    overrides = query.order_by(CollectionForecastOverride.created_at.desc()).all()
    # Populate expected_inflow_amount helper attribute
    for ovr in overrides:
        amt = Decimal(str(ovr.expected_amount)) if ovr.expected_amount is not None else Decimal("0.00")
        prob = Decimal(str(ovr.recovery_probability)) if ovr.recovery_probability is not None else Decimal("1.00")
        ovr.expected_inflow_amount = (amt * prob).quantize(Decimal("0.01"))
    return overrides


def deactivate_collection_override(
    db: Session,
    override_id: str,
) -> CollectionForecastOverride:
    """Soft-delete (deactivate) an active collection override."""
    override = (
        db.query(CollectionForecastOverride)
        .filter(CollectionForecastOverride.override_id == override_id)
        .first()
    )
    if not override:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Collection override '{override_id}' not found.",
        )

    override.is_active = False
    db.commit()
    db.refresh(override)
    return override


def create_expense_assumption(
    db: Session,
    payload: ExpenseAssumptionCreate,
) -> ExpenseForecastAssumption:
    """Create an expense forecast assumption, verifying no overlapping active periods."""
    company = db.query(Company).filter(Company.company_id == payload.company_id).first()
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company '{payload.company_id}' not found.",
        )

    if payload.effective_end_date and payload.effective_end_date < payload.effective_start_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="effective_end_date cannot be earlier than effective_start_date.",
        )

    # Check for active overlapping assumption for same company, category, and currency
    existing_overlaps = (
        db.query(ExpenseForecastAssumption)
        .filter(
            ExpenseForecastAssumption.company_id == payload.company_id,
            ExpenseForecastAssumption.category == payload.category.upper(),
            ExpenseForecastAssumption.currency == payload.currency,
            ExpenseForecastAssumption.is_active == True,
        )
        .all()
    )

    for ex in existing_overlaps:
        # Check date overlap
        ex_start = ex.effective_start_date
        ex_end = ex.effective_end_date or date.max
        new_start = payload.effective_start_date
        new_end = payload.effective_end_date or date.max

        if max(ex_start, new_start) <= min(ex_end, new_end):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Overlapping active expense assumption '{ex.assumption_id}' already covers "
                    f"category '{payload.category}' from {ex_start} to {ex.effective_end_date or 'indefinite'}."
                ),
            )

    assumption_id = f"EXP-ASM-{uuid.uuid4().hex[:12].upper()}"
    assumption = ExpenseForecastAssumption(
        assumption_id=assumption_id,
        company_id=payload.company_id,
        category=payload.category.upper(),
        monthly_amount=payload.monthly_amount,
        currency=payload.currency,
        effective_start_date=payload.effective_start_date,
        effective_end_date=payload.effective_end_date,
        description=payload.description,
        source=payload.source,
        is_active=payload.is_active,
    )
    db.add(assumption)
    db.commit()
    db.refresh(assumption)
    return assumption


def list_expense_assumptions(
    db: Session,
    company_id: str,
    category: Optional[str] = None,
    is_active: Optional[bool] = None,
) -> List[ExpenseForecastAssumption]:
    """Retrieve expense forecast assumptions."""
    query = db.query(ExpenseForecastAssumption).filter(
        ExpenseForecastAssumption.company_id == company_id
    )
    if category:
        query = query.filter(ExpenseForecastAssumption.category == category.upper())
    if is_active is not None:
        query = query.filter(ExpenseForecastAssumption.is_active == is_active)

    return query.order_by(ExpenseForecastAssumption.created_at.desc()).all()


def update_expense_assumption(
    db: Session,
    assumption_id: str,
    payload: ExpenseAssumptionUpdate,
) -> ExpenseForecastAssumption:
    """Update fields on an expense forecast assumption."""
    assumption = (
        db.query(ExpenseForecastAssumption)
        .filter(ExpenseForecastAssumption.assumption_id == assumption_id)
        .first()
    )
    if not assumption:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Expense assumption '{assumption_id}' not found.",
        )

    if payload.category is not None:
        assumption.category = payload.category.upper()
    if payload.monthly_amount is not None:
        assumption.monthly_amount = payload.monthly_amount
    if payload.currency is not None:
        assumption.currency = payload.currency
    if payload.effective_start_date is not None:
        assumption.effective_start_date = payload.effective_start_date
    if payload.effective_end_date is not None:
        assumption.effective_end_date = payload.effective_end_date
    if payload.description is not None:
        assumption.description = payload.description
    if payload.is_active is not None:
        assumption.is_active = payload.is_active

    db.commit()
    db.refresh(assumption)
    return assumption


def deactivate_expense_assumption(
    db: Session,
    assumption_id: str,
) -> ExpenseForecastAssumption:
    """Soft-delete (deactivate) an expense forecast assumption."""
    assumption = (
        db.query(ExpenseForecastAssumption)
        .filter(ExpenseForecastAssumption.assumption_id == assumption_id)
        .first()
    )
    if not assumption:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Expense assumption '{assumption_id}' not found.",
        )

    assumption.is_active = False
    db.commit()
    db.refresh(assumption)
    return assumption

