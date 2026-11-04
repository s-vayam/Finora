from fastapi.testclient import TestClient

def test_customer_crud_operations(seeded_client: TestClient):
    """Test create, retrieve, update, and validation rules for customer endpoints."""
    # 1. Create valid customer
    create_payload = {
        "company_id": "FINORA_DEMO",
        "customer_name": "Acme Global Trading Ltd",
        "country": "Germany",
        "industry": "Automotive",
        "default_payment_terms_days": 45,
    }
    res = seeded_client.post("/api/v1/customers", json=create_payload)
    assert res.status_code == 201
    created = res.json()
    assert created["customer_name"] == "Acme Global Trading Ltd"
    assert created["country"] == "Germany"
    assert created["default_payment_terms_days"] == 45
    cust_id = created["customer_id"]

    # 2. Retrieve created customer
    res_get = seeded_client.get(f"/api/v1/customers/{cust_id}")
    assert res_get.status_code == 200
    assert res_get.json()["customer_id"] == cust_id

    # 3. Update customer
    update_payload = {
        "customer_name": "Acme Global Holdings Ltd",
        "default_payment_terms_days": 60,
    }
    res_patch = seeded_client.patch(f"/api/v1/customers/{cust_id}", json=update_payload)
    assert res_patch.status_code == 200
    updated = res_patch.json()
    assert updated["customer_name"] == "Acme Global Holdings Ltd"
    assert updated["default_payment_terms_days"] == 60
    assert updated["country"] == "Germany"  # Unchanged

def test_customer_validation_errors(seeded_client: TestClient):
    """Test rejection of invalid customer payloads."""
    # Invalid company
    res_bad_company = seeded_client.post("/api/v1/customers", json={
        "company_id": "NON_EXISTENT_CO",
        "customer_name": "Ghost Corp",
        "country": "USA",
        "industry": "Tech",
        "default_payment_terms_days": 30,
    })
    assert res_bad_company.status_code == 404

    # Non-existent customer retrieve
    res_404 = seeded_client.get("/api/v1/customers/NON_EXISTENT_ID")
    assert res_404.status_code == 404

    # Empty name update
    res_empty_patch = seeded_client.patch("/api/v1/customers/CUST001", json={"customer_name": "   "})
    assert res_empty_patch.status_code == 422
