def test_golden_invoice_price_mismatch(client):
    resp = client.get("/api/fi/invoices/INV-GOLDEN-03")
    assert resp.status_code == 200
    assert resp.json()["items"][0]["unit_price"] == 140000.0


def test_invoice_not_found(client):
    resp = client.get("/api/fi/invoices/INV-DOES-NOT-EXIST")
    assert resp.status_code == 404


def test_create_invoice_auto_assigns_number_and_returns_full_fields(client):
    resp = client.post("/api/fi/invoices", json={"vendor_id": 1, "total_amount": 500})
    assert resp.status_code == 200
    body = resp.json()
    assert body["invoice_number"].startswith("INV-")
    assert body["total_amount"] == 500
    assert body["status"] == "Pending"
