"""Maintenance golden scenario end-to-end: SCADA alarm -> EquipmentAlarmEvent
-> EventBus -> AI classification -> SAP PM notification/work order.
Requires both mock-sap (8100) and mock-non-sap (8200) running."""

import time

import httpx
import pytest
from sqlmodel import select

from app.models_platform import AIDecision, Event, IntegrationLog
from tests.conftest import TEST_ENGINE, auth_headers

SAP_URL = "http://127.0.0.1:8100"
NONSAP_URL = "http://127.0.0.1:8200"


def _up(url: str) -> bool:
    try:
        return httpx.get(f"{url}/api/health", timeout=1.0).status_code == 200
    except httpx.HTTPError:
        return False


pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not (_up(SAP_URL) and _up(NONSAP_URL)), reason="mock-sap and/or mock-non-sap not running"),
]


def test_maintenance_work_order_golden_scenario(client):
    headers = auth_headers(client, "admin")
    workflows = client.get("/api/workflows", headers=headers).json()
    maint_wo = next(w for w in workflows if w["key"] == "MAINT_WO")

    resp = client.post(f"/api/runs?workflow_id={maint_wo['id']}", headers=headers)
    assert resp.status_code == 201
    run = resp.json()

    deadline = time.time() + 30
    final = run
    while time.time() < deadline:
        final = client.get(f"/api/runs/{run['id']}", headers=headers).json()
        if final["status"] in ("Completed", "Exception"):
            break
        time.sleep(0.5)

    # The vibration alarm (12.0 vs threshold 5.0) is a 2.4x ratio -> Emergency
    # priority per MockAIProvider.classify_maintenance_alarm, which always
    # completes the work-order creation steps (not itself an exception path).
    assert final["status"] == "Completed"
    assert "work order" in final["result_summary"].lower()

    log_steps = {entry["step"] for entry in final["log"]}
    assert "Receive equipment alert from SCADA/IoT" in log_steps
    assert "Create maintenance notification in SAP PM" in log_steps
    assert "Create and assign work order" in log_steps

    from sqlmodel import Session

    with Session(TEST_ENGINE) as session:
        ai_decisions = session.exec(
            select(AIDecision).where(AIDecision.use_case == "maintenance_alarm_classification")
        ).all()
        assert any(d.workflow_run_id == run["id"] for d in ai_decisions)

        sap_logs = session.exec(
            select(IntegrationLog).where(IntegrationLog.workflow_run_id == run["id"])
        ).all()
        assert any(log.system == "SAP PM" for log in sap_logs)

        events = session.exec(select(Event).where(Event.event_type == "equipment_alarm")).all()
        assert len(events) > 0
