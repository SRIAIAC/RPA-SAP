from app.seed.generate_synthetic_data import GOLDEN_EQUIPMENT_ID


def test_get_golden_equipment(client):
    resp = client.get(f"/api/pm/equipment/{GOLDEN_EQUIPMENT_ID}")
    assert resp.status_code == 200
    assert resp.json()["criticality"] == "Critical"


def test_create_work_order_for_unknown_equipment_returns_404(client):
    resp = client.post("/api/pm/work-orders", json={"equipment_id": "EQ-NOT-REAL", "priority": "Routine"})
    assert resp.status_code == 404


def test_create_work_order_auto_assigns_number(client):
    resp = client.post(
        "/api/pm/work-orders", json={"equipment_id": GOLDEN_EQUIPMENT_ID, "priority": "Emergency"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["order_number"].startswith("WO-")
    assert body["equipment_id"] == GOLDEN_EQUIPMENT_ID


def test_create_notification_auto_assigns_number(client):
    resp = client.post(
        "/api/pm/notifications",
        json={"equipment_id": GOLDEN_EQUIPMENT_ID, "description": "Vibration alarm", "priority": "Emergency"},
    )
    assert resp.status_code == 200
    assert resp.json()["notification_number"].startswith("NOTIF-")
