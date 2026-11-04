from fastapi.testclient import TestClient

def test_empty_database_responses(client: TestClient):
    """Test read-only endpoints against an empty database."""
    # Seed status
    res = client.get("/api/v1/meta/seed-status")
    assert res.status_code == 200
    assert res.json()["seeded"] is False
    assert res.json()["dataset_id"] is None

    # Data summary
    res = client.get("/api/v1/meta/data-summary")
    assert res.status_code == 200
    summary = res.json()
    assert summary["total_customers"] == 0
    assert summary["total_invoices"] == 0
    assert summary["available_historical_months"] == 0
    assert summary["dataset_date_range"]["start_date"] is None

    # Customers
    res = client.get("/api/v1/customers")
    assert res.status_code == 200
    assert res.json()["total"] == 0
    assert res.json()["items"] == []

    # Invoices
    res = client.get("/api/v1/invoices")
    assert res.status_code == 200
    assert res.json()["total"] == 0
    assert res.json()["items"] == []

    # Expenses
    res = client.get("/api/v1/expenses")
    assert res.status_code == 200
    assert res.json()["total"] == 0
    assert res.json()["items"] == []

    # Transactions
    res = client.get("/api/v1/transactions")
    assert res.status_code == 200
    assert res.json()["total"] == 0
    assert res.json()["items"] == []

    # Cashflow history
    res = client.get("/api/v1/cashflow/history")
    assert res.status_code == 200
    assert res.json() == []

def test_seeded_meta_endpoints(seeded_client: TestClient):
    """Test /meta/seed-status and /meta/data-summary on seeded database."""
    # Seed Status
    res = seeded_client.get("/api/v1/meta/seed-status")
    assert res.status_code == 200
    data = res.json()
    assert data["seeded"] is True
    assert data["dataset_id"] == "FINORA_DEMO"
    assert data["record_counts"]["customers"] == 60
    assert data["record_counts"]["invoices"] == 899
    assert data["record_counts"]["expenses"] == 872
    assert data["record_counts"]["cash_transactions"] == 1722
    assert data["record_counts"]["monthly_cashflow"] == 36

    # Data Summary
    res = seeded_client.get("/api/v1/meta/data-summary")
    assert res.status_code == 200
    summary = res.json()
    assert summary["total_customers"] == 60
    assert summary["total_invoices"] == 899
    assert summary["total_paid_invoices"] == 873
    assert summary["total_open_invoices"] == 26
    assert summary["total_expenses"] == 872
    assert summary["total_cash_transactions"] == 1722
    assert summary["available_historical_months"] == 36
    assert summary["dataset_date_range"]["start_date"] is not None
    assert summary["dataset_date_range"]["end_date"] is not None

def test_customers_pagination(seeded_client: TestClient):
    """Test customer listing with pagination."""
    res = seeded_client.get("/api/v1/customers?page=1&page_size=10")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 60
    assert data["page"] == 1
    assert data["page_size"] == 10
    assert data["total_pages"] == 6
    assert len(data["items"]) == 10

    # Page 2
    res2 = seeded_client.get("/api/v1/customers?page=2&page_size=10")
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["page"] == 2
    assert data2["items"][0]["customer_id"] != data["items"][0]["customer_id"]

def test_invoices_pagination_and_filters(seeded_client: TestClient):
    """Test invoice listing with filtering by customer, status, and currency."""
    # All invoices paginated
    res = seeded_client.get("/api/v1/invoices?page=1&page_size=20")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 899
    assert len(data["items"]) == 20

    # Filter by customer_id
    res_cust = seeded_client.get("/api/v1/invoices?customer_id=CUST001")
    assert res_cust.status_code == 200
    data_cust = res_cust.json()
    assert data_cust["total"] > 0
    for inv in data_cust["items"]:
        assert inv["customer_id"] == "CUST001"

    # Filter by status = PAID
    res_paid = seeded_client.get("/api/v1/invoices?status=PAID")
    assert res_paid.status_code == 200
    assert res_paid.json()["total"] == 873

    # Filter by status = OPEN
    res_open = seeded_client.get("/api/v1/invoices?status=OPEN")
    assert res_open.status_code == 200
    assert res_open.json()["total"] == 26

    # Filter by currency = INR
    res_curr = seeded_client.get("/api/v1/invoices?currency=INR")
    assert res_curr.status_code == 200
    assert res_curr.json()["total"] == 899

def test_expenses_pagination_and_filter(seeded_client: TestClient):
    """Test expense listing with category filter."""
    res = seeded_client.get("/api/v1/expenses?page=1&page_size=15")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 872
    assert len(data["items"]) == 15

    # Filter by category SALARIES (36 months -> 36 records)
    res_sal = seeded_client.get("/api/v1/expenses?category=SALARIES")
    assert res_sal.status_code == 200
    data_sal = res_sal.json()
    assert data_sal["total"] == 36
    for exp in data_sal["items"]:
        assert exp["category"] == "SALARIES"

def test_transactions_pagination_and_filters(seeded_client: TestClient):
    """Test cash transactions with transaction_type and date filters."""
    res = seeded_client.get("/api/v1/transactions?page=1&page_size=25")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 1722
    assert len(data["items"]) == 25

    # Filter by type = INFLOW
    res_inflow = seeded_client.get("/api/v1/transactions?transaction_type=INFLOW")
    assert res_inflow.status_code == 200
    assert res_inflow.json()["total"] == 873

    # Filter by type = OUTFLOW
    res_outflow = seeded_client.get("/api/v1/transactions?transaction_type=OUTFLOW")
    assert res_outflow.status_code == 200
    assert res_outflow.json()["total"] == 849

    # Filter by date range (e.g. year 2023)
    res_date = seeded_client.get("/api/v1/transactions?start_date=2023-01-01&end_date=2023-12-31")
    assert res_date.status_code == 200
    txns_2023 = res_date.json()["items"]
    for txn in txns_2023:
        assert txn["transaction_date"] >= "2023-01-01"
        assert txn["transaction_date"] <= "2023-12-31"

def test_cashflow_history(seeded_client: TestClient):
    """Test historical monthly cashflow endpoint returns 36 ordered months."""
    res = seeded_client.get("/api/v1/cashflow/history")
    assert res.status_code == 200
    months = res.json()
    assert len(months) == 36
    assert months[0]["month"] == "2023-01"
    assert months[-1]["month"] == "2025-12"

    # Verify chronological sequence
    for i in range(1, len(months)):
        assert months[i]["month"] > months[i - 1]["month"]

def test_invalid_request_handling(client: TestClient):
    """Test validation errors for invalid query parameters."""
    # Invalid page number (< 1)
    res_page = client.get("/api/v1/customers?page=0")
    assert res_page.status_code == 422
    assert "errors" in res_page.json()

    # Invalid date string format
    res_date = client.get("/api/v1/transactions?start_date=not-a-valid-date")
    assert res_date.status_code == 422
    assert "errors" in res_date.json()

