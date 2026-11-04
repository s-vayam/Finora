from datetime import datetime, date
from decimal import Decimal
import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy import inspect

from app.models.company import Company
from app.models.customer import Customer
from app.models.invoice import Invoice
from app.models.monthly_cashflow import MonthlyCashflow

def test_database_initialization_and_tables(test_db_session: Session):
    """Test that all required tables are created in the database."""
    engine = test_db_session.get_bind()
    inspector = inspect(engine)
    table_names = inspector.get_table_names()

    required_tables = [
        "companies",
        "customers",
        "invoices",
        "expenses",
        "cash_transactions",
        "monthly_cashflow",
    ]

    for table in required_tables:
        assert table in table_names, f"Table '{table}' was not created in database"

def test_foreign_key_enforcement_customer(test_db_session: Session):
    """Test that creating a customer with invalid company_id fails under PRAGMA foreign_keys."""
    invalid_customer = Customer(
        customer_id="CUST_NON_EXISTENT",
        company_id="INVALID_COMPANY_ID",
        customer_name="Ghost Co.",
        country="India",
        industry="Retail",
        default_payment_terms_days=30,
    )
    test_db_session.add(invalid_customer)
    with pytest.raises(IntegrityError):
        test_db_session.commit()
    test_db_session.rollback()

def test_foreign_key_enforcement_invoice(test_db_session: Session):
    """Test that creating an invoice with non-existent customer fails."""
    # First create valid company
    company = Company(
        company_id="COMP_TEST",
        company_name="Test Company",
        base_currency="INR",
        created_at=datetime.utcnow(),
    )
    test_db_session.add(company)
    test_db_session.commit()

    # Create invoice referencing non-existent customer
    invalid_invoice = Invoice(
        invoice_id="INV_GHOST",
        company_id="COMP_TEST",
        customer_id="NON_EXISTENT_CUST",
        invoice_date=date(2023, 1, 1),
        due_date=date(2023, 1, 31),
        payment_terms_days=30,
        invoice_amount=Decimal("10000.00"),
        currency="INR",
        status="OPEN",
    )
    test_db_session.add(invalid_invoice)
    with pytest.raises(IntegrityError):
        test_db_session.commit()
    test_db_session.rollback()

def test_unique_constraint_monthly_cashflow(test_db_session: Session):
    """Test that inserting duplicate (company_id, month) violates unique constraint."""
    company = Company(
        company_id="COMP_TEST_CF",
        company_name="Test CF Company",
        base_currency="INR",
        created_at=datetime.utcnow(),
    )
    test_db_session.add(company)
    test_db_session.commit()

    cf1 = MonthlyCashflow(
        company_id="COMP_TEST_CF",
        month="2023-01",
        opening_balance=Decimal("1000000.00"),
        actual_inflows=Decimal("200000.00"),
        actual_outflows=Decimal("150000.00"),
        net_cash_flow=Decimal("50000.00"),
        closing_balance=Decimal("1050000.00"),
        inflow_transactions=5,
        outflow_transactions=4,
        currency="INR",
    )
    test_db_session.add(cf1)
    test_db_session.commit()

    # Try duplicate entry for same company and month
    cf2 = MonthlyCashflow(
        company_id="COMP_TEST_CF",
        month="2023-01",
        opening_balance=Decimal("1050000.00"),
        actual_inflows=Decimal("300000.00"),
        actual_outflows=Decimal("250000.00"),
        net_cash_flow=Decimal("50000.00"),
        closing_balance=Decimal("1100000.00"),
        inflow_transactions=6,
        outflow_transactions=5,
        currency="INR",
    )
    test_db_session.add(cf2)
    with pytest.raises(IntegrityError):
        test_db_session.commit()
    test_db_session.rollback()

def test_primary_key_constraint(test_db_session: Session):
    """Test that inserting duplicate primary key raises IntegrityError."""
    comp1 = Company(
        company_id="COMP_DUP",
        company_name="Company 1",
        base_currency="INR",
    )
    test_db_session.add(comp1)
    test_db_session.commit()

    test_db_session.expunge(comp1)
    comp2 = Company(
        company_id="COMP_DUP",
        company_name="Company 2",
        base_currency="INR",
    )
    test_db_session.add(comp2)
    with pytest.raises(IntegrityError):
        test_db_session.commit()
    test_db_session.rollback()
