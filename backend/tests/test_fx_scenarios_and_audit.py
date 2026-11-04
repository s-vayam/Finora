import datetime
from decimal import Decimal
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, func, text

from app.database import SessionLocal
from app.main import app
from app.models.company import Company
from app.models.customer import Customer
from app.models.invoice import Invoice
from app.models.payment import Payment
from app.models.expense import Expense
from app.models.cash_transaction import CashTransaction
from app.models.monthly_cashflow import MonthlyCashflow
from app.models.fx_scenario_run import FxScenarioRun


@pytest.fixture(scope="module")
def fx_client():
    """Test client using operational database for scenario and audit tests."""
    with TestClient(app) as client:
        yield client


def test_percentage_movement_scenario_positive(fx_client: TestClient):
    payload = {
        "company_id": "FINORA_DEMO",
        "currency_pair": "USD/INR",
        "scenario_type": "PERCENTAGE_MOVEMENT",
        "percentage_change": "5.0"
    }
    response = fx_client.post("/api/v1/fx/scenario", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["company_id"] == "FINORA_DEMO"
    assert data["currency_pair"] == "USD/INR"
    bench = float(data["benchmark_rate"])
    scen = float(data["scenario_rate"])
    pct = float(data["percentage_change"])
    assert pct == 5.0
    assert abs(scen - (bench * 1.05)) < 0.05

    rec_exp = float(data["receivable_exposure"])
    pay_exp = float(data["payable_exposure"])
    rec_imp = float(data["estimated_receivable_impact"])
    pay_imp = float(data["estimated_payable_impact"])
    net_imp = float(data["net_estimated_impact"])

    # Math consistency
    delta = scen - bench
    expected_rec_imp = round(rec_exp * delta, 2)
    expected_pay_imp = round(-pay_exp * delta, 2)
    assert abs(rec_imp - expected_rec_imp) < 0.1
    assert abs(pay_imp - expected_pay_imp) < 0.1
    assert abs(net_imp - (rec_imp + pay_imp)) < 0.05

    # With a positive shift, receivables benefit and payables cost more
    if rec_exp > 0:
        assert rec_imp > 0
    if pay_exp > 0:
        assert pay_imp < 0

    # ML comparison check
    assert data["comparison_with_ml"] is not None
    ml_comp = data["comparison_with_ml"]
    assert "ml_predicted_rate" in ml_comp
    assert "divergence_bps" in ml_comp


def test_percentage_movement_scenario_negative(fx_client: TestClient):
    payload = {
        "company_id": "FINORA_DEMO",
        "currency_pair": "USD/INR",
        "scenario_type": "PERCENTAGE_MOVEMENT",
        "percentage_change": "-5.0"
    }
    response = fx_client.post("/api/v1/fx/scenario", json=payload)
    assert response.status_code == 200
    data = response.json()

    bench = float(data["benchmark_rate"])
    scen = float(data["scenario_rate"])
    assert scen < bench

    rec_exp = float(data["receivable_exposure"])
    pay_exp = float(data["payable_exposure"])
    rec_imp = float(data["estimated_receivable_impact"])
    pay_imp = float(data["estimated_payable_impact"])

    if rec_exp > 0:
        assert rec_imp < 0
    if pay_exp > 0:
        assert pay_imp > 0


def test_target_rate_scenario(fx_client: TestClient):
    # Benchmark is around 94-95 for USD/INR; test target rate 96.0
    payload = {
        "company_id": "FINORA_DEMO",
        "currency_pair": "USD/INR",
        "scenario_type": "TARGET_RATE",
        "scenario_rate": "96.0000"
    }
    response = fx_client.post("/api/v1/fx/scenario", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert float(data["scenario_rate"]) == 96.0
    bench = float(data["benchmark_rate"])
    expected_pct = ((96.0 - bench) / bench) * 100.0
    assert abs(float(data["percentage_change"]) - expected_pct) < 0.05


def test_scenario_validation_errors(fx_client: TestClient):
    # Exceeding +25% bound
    res_pos = fx_client.post("/api/v1/fx/scenario", json={
        "company_id": "FINORA_DEMO",
        "currency_pair": "USD/INR",
        "scenario_type": "PERCENTAGE_MOVEMENT",
        "percentage_change": "26.0"
    })
    assert res_pos.status_code == 422

    # Exceeding -25% bound
    res_neg = fx_client.post("/api/v1/fx/scenario", json={
        "company_id": "FINORA_DEMO",
        "currency_pair": "USD/INR",
        "scenario_type": "PERCENTAGE_MOVEMENT",
        "percentage_change": "-30.0"
    })
    assert res_neg.status_code == 422

    # Target rate exceeding allowable 25% movement
    res_target = fx_client.post("/api/v1/fx/scenario", json={
        "company_id": "FINORA_DEMO",
        "currency_pair": "USD/INR",
        "scenario_type": "TARGET_RATE",
        "scenario_rate": "150.0000"
    })
    assert res_target.status_code == 422

    # Unsupported currency pair
    res_curr = fx_client.post("/api/v1/fx/scenario", json={
        "company_id": "FINORA_DEMO",
        "currency_pair": "JPY/INR",
        "scenario_type": "PERCENTAGE_MOVEMENT",
        "percentage_change": "5.0"
    })
    assert res_curr.status_code == 422


def test_scenario_retrieval_and_history(fx_client: TestClient):
    payload = {
        "company_id": "FINORA_DEMO",
        "currency_pair": "EUR/INR",
        "scenario_type": "PERCENTAGE_MOVEMENT",
        "percentage_change": "3.5"
    }
    create_res = fx_client.post("/api/v1/fx/scenario", json=payload)
    assert create_res.status_code == 200
    sc_id = create_res.json()["scenario_id"]

    # Fetch by ID
    get_res = fx_client.get(f"/api/v1/fx/scenarios/{sc_id}")
    assert get_res.status_code == 200
    assert get_res.json()["scenario_id"] == sc_id
    assert get_res.json()["currency_pair"] == "EUR/INR"

    # Non-existent ID
    err_res = fx_client.get("/api/v1/fx/scenarios/non-existent-uuid")
    assert err_res.status_code == 404

    # History list
    hist_res = fx_client.get("/api/v1/fx/scenarios/history?company_id=FINORA_DEMO&limit=10")
    assert hist_res.status_code == 200
    items = hist_res.json()
    assert isinstance(items, list)
    assert len(items) >= 1
    assert items[0]["company_id"] == "FINORA_DEMO"


def test_financial_database_integrity_post_phase5():
    """Verify that historical business data remains 100% uncorrupted after Phase 5."""
    session = SessionLocal()
    try:
        # 1. Company
        comp_count = session.scalar(select(func.count(Company.company_id)))
        assert comp_count == 1, f"Expected 1 company, got {comp_count}"

        # 2. Customers
        cust_count = session.scalar(select(func.count(Customer.customer_id)))
        assert cust_count == 60, f"Expected 60 customers, got {cust_count}"

        # 3. Invoices
        inv_count = session.scalar(select(func.count(Invoice.invoice_id)))
        assert inv_count == 899, f"Expected 899 invoices, got {inv_count}"

        paid_invoices = session.scalar(
            select(func.count(Invoice.invoice_id)).where(Invoice.status == "PAID")
        )
        assert paid_invoices == 873, f"Expected 873 paid invoices, got {paid_invoices}"

        open_invoices = session.scalar(
            select(func.count(Invoice.invoice_id)).where(Invoice.status != "PAID")
        )
        assert open_invoices == 26, f"Expected 26 open invoices, got {open_invoices}"

        # 4. Payments
        pmt_count = session.scalar(select(func.count(Payment.payment_id)))
        assert pmt_count == 873, f"Expected 873 payments, got {pmt_count}"

        # 5. Expenses
        exp_count = session.scalar(select(func.count(Expense.expense_id)))
        assert exp_count == 872, f"Expected 872 expenses, got {exp_count}"

        # 6. Cash transactions
        tx_count = session.scalar(select(func.count(CashTransaction.transaction_id)))
        assert tx_count == 1722, f"Expected 1722 cash transactions, got {tx_count}"

        # 7. Monthly cash flow
        cf_count = session.scalar(select(func.count(MonthlyCashflow.id)))
        assert cf_count == 36, f"Expected 36 monthly cash flows, got {cf_count}"

        # 8. SQLite foreign key and integrity check
        integrity = session.execute(text("PRAGMA integrity_check")).fetchone()[0]
        assert integrity == "ok", f"Integrity check failed: {integrity}"

        fk_check = session.execute(text("PRAGMA foreign_key_check")).fetchall()
        assert len(fk_check) == 0, f"Foreign key check violations found: {fk_check}"
    finally:
        session.close()
