from app.seed.generate_synthetic_data import GOLDEN_CRUDE_PO_NUMBER, GOLDEN_EQUIPMENT_ID


def test_golden_scada_alarm_present(client):
    resp = client.get("/api/scada/alarms", params={"equipment_id": GOLDEN_EQUIPMENT_ID})
    assert resp.status_code == 200
    alarms = resp.json()
    assert len(alarms) == 1
    assert alarms[0]["value"] == 12.0
    assert alarms[0]["threshold"] == 5.0


def test_equipment_telemetry_returns_readings(client):
    resp = client.get(f"/api/scada/equipment/{GOLDEN_EQUIPMENT_ID}/telemetry")
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


def test_golden_crude_terminal_and_tank_readings(client):
    receipts = client.get("/api/terminal/receipts", params={"po_number": GOLDEN_CRUDE_PO_NUMBER}).json()
    tanks = client.get("/api/terminal/tank-readings", params={"po_number": GOLDEN_CRUDE_PO_NUMBER}).json()
    assert receipts[0]["quantity_bbl"] == 9950.0
    assert tanks[0]["quantity_bbl"] == 9850.0


def test_wms_inventory_list(client):
    resp = client.get("/api/wms/inventory")
    assert resp.status_code == 200
    assert len(resp.json()) > 0


def test_crm_customers_and_orders(client):
    customers = client.get("/api/crm/customers").json()
    assert len(customers) > 0
    orders = client.get("/api/crm/orders").json()
    assert isinstance(orders, list)


def test_supplier_documents_and_onboarding(client):
    docs = client.get("/api/supplier/documents").json()
    assert len(docs) > 0
    resp = client.post("/api/supplier/onboarding", json={"vendor_name": "Test Vendor Pvt Ltd"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "Submitted"


def test_email_inbox_and_send(client):
    inbox = client.get("/api/email/inbox").json()
    assert len(inbox) > 0
    resp = client.post("/api/email/send", json={"subject": "Test", "body": "Hello", "department": "Procurement"})
    assert resp.status_code == 200
    assert resp.json()["subject"] == "Test"


def test_lims_results(client):
    resp = client.get("/api/lims/test-results")
    assert resp.status_code == 200
    assert len(resp.json()) > 0


def test_document_repository_get_and_404(client):
    resp = client.get("/api/documents/DOC-700001")
    assert resp.status_code == 200
    missing = client.get("/api/documents/DOC-DOES-NOT-EXIST")
    assert missing.status_code == 404
