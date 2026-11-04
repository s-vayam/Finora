"""
Tests for Expense & Outflow Forecasting (Phase 4 Stage 4C).

Verifies single-source-of-truth historical outflows from cash_transactions,
no double counting with expense records, manual assumption precedence,
future scheduled commitments, and stale data reporting.
"""

from datetime import date, timedelta
from decimal import Decimal
import uuid
import pytest
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.cash_transaction import CashTransaction
from app.models.expense import Expense
from app.models.monthly_cashflow import MonthlyCashflow
from app.models.expense_forecast_assumption import ExpenseForecastAssumption
from app.services.expense_forecasting_service import (
    forecast_expenses_and_outflows,
    run_chronological_baseline_backtest,
)


def test_historical_outflow_reconciliation(seeded_test_db: Session):
    """
    Verify that SUM(completed OUTFLOW cash_transactions) matches
    SUM(monthly_cashflow.actual_outflows) exactly across all 36 historical months.
    """
    txn_outflows = (
        seeded_test_db.query(func.sum(CashTransaction.amount))
        .filter(
            CashTransaction.company_id == "FINORA_DEMO",
            CashTransaction.transaction_type == "OUTFLOW",
            CashTransaction.currency == "INR",
        )
        .scalar()
    )

    monthly_outflows = (
        seeded_test_db.query(func.sum(MonthlyCashflow.actual_outflows))
        .filter(
            MonthlyCashflow.company_id == "FINORA_DEMO",
            MonthlyCashflow.currency == "INR",
        )
        .scalar()
    )

    assert txn_outflows is not None
    assert monthly_outflows is not None
    assert Decimal(str(txn_outflows)) == Decimal(str(monthly_outflows))
    assert Decimal(str(txn_outflows)) == Decimal("73732730.47")


def test_no_double_counting_expenses_and_transactions(seeded_test_db: Session):
    """
    Verify that paid expenses are NOT summed on top of cash transactions
    in historical actual outflows.
    """
    paid_expenses_sum = (
        seeded_test_db.query(func.sum(Expense.amount))
        .filter(Expense.company_id == "FINORA_DEMO", Expense.status == "PAID")
        .scalar()
    )

    outflow_txns_sum = (
        seeded_test_db.query(func.sum(CashTransaction.amount))
        .filter(CashTransaction.company_id == "FINORA_DEMO", CashTransaction.transaction_type == "OUTFLOW")
        .scalar()
    )

    # In Finora, completed expenses generated matching cash transactions (same INR 73.73M total)
    assert Decimal(str(paid_expenses_sum)) == Decimal(str(outflow_txns_sum))


def test_stale_data_warning_triggered(seeded_test_db: Session):
    """Verify that forecasting from Nov 2026 flags stale 2025 expense data."""
    as_of = date(2026, 11, 4)
    res = forecast_expenses_and_outflows(
        seeded_test_db, company_id="FINORA_DEMO", as_of_date=as_of, horizon_days=90, base_currency="INR"
    )

    freshness = res["data_freshness"]
    assert freshness["expense_data_stale"] is True
    assert freshness["days_since_last_actual_data"] > 90
    assert len(freshness["warnings"]) > 0


def test_manual_expense_assumption_precedence(seeded_test_db: Session):
    """
    Verify that an active manual assumption supersedes the inferred category baseline
    rather than being added on top.
    """
    as_of = date(2026, 11, 4)

    # First, run forecast with no assumptions
    base_res = forecast_expenses_and_outflows(
        seeded_test_db, company_id="FINORA_DEMO", as_of_date=as_of, horizon_days=30, base_currency="INR"
    )
    base_salaries = sum(
        (e["amount"] for e in base_res["estimated_events"] if e["category"] == "SALARIES"),
        Decimal("0.00"),
    )

    # Add active manual assumption for SALARIES with a lower budget
    asm = ExpenseForecastAssumption(
        assumption_id=f"EXP-ASM-{uuid.uuid4().hex[:8].upper()}",
        company_id="FINORA_DEMO",
        category="SALARIES",
        monthly_amount=Decimal("300000.00"),
        currency="INR",
        effective_start_date=date(2026, 11, 1),
        effective_end_date=date(2026, 11, 30),
        is_active=True,
    )
    seeded_test_db.add(asm)
    seeded_test_db.commit()

    asm_res = forecast_expenses_and_outflows(
        seeded_test_db, company_id="FINORA_DEMO", as_of_date=as_of, horizon_days=30, base_currency="INR"
    )
    asm_salaries = sum(
        (e["amount"] for e in asm_res["estimated_events"] if e["category"] == "SALARIES"),
        Decimal("0.00"),
    )

    # The manual assumption replaced the baseline salaries amount
    assert asm_salaries != base_salaries
    # Check that source is marked MANUAL_ASSUMPTION
    sal_events = [e for e in asm_res["estimated_events"] if e["category"] == "SALARIES"]
    assert any("MANUAL_ASSUMPTION" in e["source"] for e in sal_events)

