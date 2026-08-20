from app.seed.generate_synthetic_data import GOLDEN_EXPIRED_VENDOR_CODE, GOLDEN_VENDOR_CODE


def test_get_golden_vendor(client):
    resp = client.get(f"/api/mm/vendors/{GOLDEN_VENDOR_CODE}")
    assert resp.status_code == 200
    assert resp.json()["name"] == "Deccan Valves & Fittings Pvt Ltd"


def test_golden_vendor_has_expired_insurance(client):
    resp = client.get(f"/api/mm/vendors/{GOLDEN_EXPIRED_VENDOR_CODE}")
    assert resp.status_code == 200
    assert resp.json()["insurance_expiry"] < "2026-08-19"  # seeded in the past relative to any "today"


def test_vendor_not_found(client):
    resp = client.get("/api/mm/vendors/V-DOES-NOT-EXIST")
    assert resp.status_code == 404


def test_golden_po_has_items(client):
    resp = client.get("/api/mm/purchase-orders/PO-GOLDEN-01")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["items"]) == 1
    assert body["items"][0]["quantity"] == 4


def test_golden_grn_scenario1_matches_po_exactly(client):
    resp = client.get("/api/mm/goods-receipts/PO-GOLDEN-01")
    assert resp.status_code == 200
    assert resp.json()["items"][0]["quantity_received"] == 4


def test_golden_grn_scenario2_short_received(client):
    resp = client.get("/api/mm/goods-receipts/PO-GOLDEN-02")
    assert resp.status_code == 200
    assert resp.json()["items"][0]["quantity_received"] == 3


def test_golden_po05_has_no_grn(client):
    resp = client.get("/api/mm/goods-receipts/PO-GOLDEN-05")
    assert resp.status_code == 404


def test_create_purchase_order_auto_assigns_number(client):
    resp = client.post("/api/mm/purchase-orders", json={"vendor_id": 1})
    assert resp.status_code == 200
    body = resp.json()
    assert body["po_number"].startswith("PO-")
    assert body["items"] == []


def test_list_contracts_expiring_within_30_days_includes_golden_contract(client):
    resp = client.get("/api/mm/contracts", params={"expiring_within_days": 30})
    assert resp.status_code == 200
    numbers = [c["contract_number"] for c in resp.json()]
    assert "CTR-GOLDEN-01" in numbers
