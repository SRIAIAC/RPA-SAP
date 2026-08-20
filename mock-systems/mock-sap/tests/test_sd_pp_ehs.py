def test_get_customer(client):
    resp = client.get("/api/sd/customers/C-700001")
    assert resp.status_code == 200
    assert resp.json()["customer_code"] == "C-700001"


def test_create_sales_order_fully_populated_even_with_no_items(client):
    resp = client.post("/api/sd/sales-orders", json={"customer_id": 1})
    assert resp.status_code == 200
    body = resp.json()
    assert body["so_number"].startswith("SO-")
    assert body["status"] == "Created"
    assert body["items"] == []


def test_list_production_orders_includes_records(client):
    resp = client.get("/api/pp/production-orders")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) > 0
    assert "records" in body[0]


def test_create_hse_incident_with_known_equipment(client):
    from app.seed.generate_synthetic_data import GOLDEN_EQUIPMENT_ID

    resp = client.post(
        "/api/ehs/incidents",
        json={"description": "Test spill", "severity": "Medium", "equipment_id": GOLDEN_EQUIPMENT_ID},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["incident_number"].startswith("HSE-")
    assert body["equipment_found_in_asset_master"] is True


def test_create_hse_incident_with_unknown_equipment_still_creates_record(client):
    # HSE KB #10: safety reporting is never blocked on missing equipment data quality.
    resp = client.post(
        "/api/ehs/incidents",
        json={"description": "Test spill", "severity": "Low", "equipment_id": "EQ-DOES-NOT-EXIST"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["equipment_found_in_asset_master"] is False
